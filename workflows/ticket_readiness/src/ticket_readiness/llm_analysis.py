from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from ticket_readiness.http_config import validate_timeout_seconds
from ticket_readiness.linear import LinearIssue
from ticket_readiness.rate_limit import RateLimitError
from ticket_readiness.readiness import DeterministicReadinessResult
from ticket_readiness.security import contains_secret_like_value

OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5-mini"

READINESS_STATUSES = {"ready", "needs_grooming", "blocked", "not_ready"}
RISK_LEVELS = {"low", "medium", "high"}

REQUIRED_OUTPUT_FIELDS = (
    "summary",
    "work_type",
    "risk_level",
    "readiness_status",
    "missing_information",
    "grooming_questions",
    "operational_risk",
    "security_notes",
    "acceptance_criteria_improvements",
    "recommended_next_action",
    "draft_comment",
)

LIST_FIELDS = (
    "missing_information",
    "grooming_questions",
    "operational_risk",
    "security_notes",
    "acceptance_criteria_improvements",
)


class LLMAnalysisError(RuntimeError):
    """Raised when model analysis cannot be trusted."""


class OpenAIResponseClient(Protocol):
    def create_response(self, **kwargs: Any) -> dict[str, Any]:
        """Create an OpenAI response."""


class RateLimiter(Protocol):
    def wait(self) -> None:
        """Throttle before an external API call."""


@dataclass(frozen=True)
class LLMAnalysis:
    summary: str
    work_type: str
    risk_level: str
    readiness_status: str
    missing_information: tuple[str, ...]
    grooming_questions: tuple[str, ...]
    operational_risk: tuple[str, ...]
    security_notes: tuple[str, ...]
    acceptance_criteria_improvements: tuple[str, ...]
    recommended_next_action: str
    draft_comment: str
    model_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for field_name in LIST_FIELDS:
            payload[field_name] = list(getattr(self, field_name))
        return payload


class HTTPOpenAIClient:
    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = OPENAI_RESPONSES_ENDPOINT,
        timeout_seconds: int = 60,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._endpoint = endpoint
        self._timeout_seconds = validate_timeout_seconds(timeout_seconds)
        self._rate_limiter = rate_limiter

    def create_response(self, **kwargs: Any) -> dict[str, Any]:
        if not self._api_key:
            raise LLMAnalysisError("OPENAI_API_KEY is required for live LLM analysis.")

        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(kwargs).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        try:
            if self._rate_limiter is not None:
                self._rate_limiter.wait()
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise LLMAnalysisError("OpenAI response request was rate limited.") from RateLimitError(
                    "OpenAI response request was rate limited."
                )
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMAnalysisError(
                f"OpenAI response request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMAnalysisError(f"OpenAI response request failed: {exc.reason}") from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise LLMAnalysisError("OpenAI response was not valid JSON.") from exc


class LLMAnalysisAdapter:
    def __init__(self, client: OpenAIResponseClient, model: str = DEFAULT_MODEL) -> None:
        self._client = client
        self._model = model

    def analyze(
        self,
        *,
        issue: LinearIssue,
        rubric: dict[str, Any],
        deterministic_result: DeterministicReadinessResult,
    ) -> LLMAnalysis:
        response = self._client.create_response(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": _system_prompt(),
                },
                {
                    "role": "user",
                    "content": build_analysis_prompt(
                        issue=issue,
                        rubric=rubric,
                        deterministic_result=deterministic_result,
                    ),
                },
            ],
            text={"format": analysis_response_format()},
        )

        output = _extract_output(response)
        analysis = validate_model_output(output)
        return _with_metadata(analysis, response)


def build_analysis_prompt(
    *,
    issue: LinearIssue,
    rubric: dict[str, Any],
    deterministic_result: DeterministicReadinessResult,
) -> str:
    payload = {
        "issue": issue.to_dict(),
        "rubric": rubric,
        "deterministic_findings": deterministic_result.to_dict(),
    }
    return (
        "Use only the following Issue Snapshot, Readiness Rubric, and "
        "Deterministic Findings. Separate evidence from inference, preserve "
        "uncertainty, and do not recommend direct infrastructure mutation.\n\n"
        "Issue Snapshot:\n"
        f"{json.dumps(payload['issue'], indent=2, sort_keys=True)}\n\n"
        "Readiness Rubric:\n"
        f"{json.dumps(payload['rubric'], indent=2, sort_keys=True)}\n\n"
        "Deterministic Findings:\n"
        f"{json.dumps(payload['deterministic_findings'], indent=2, sort_keys=True)}"
    )


def validate_model_output(raw_output: str | dict[str, Any]) -> LLMAnalysis:
    if isinstance(raw_output, str):
        try:
            output = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise LLMAnalysisError("Model output was not valid JSON.") from exc
    else:
        output = raw_output

    if not isinstance(output, dict):
        raise LLMAnalysisError("Model output must be a JSON object.")

    for field_name in REQUIRED_OUTPUT_FIELDS:
        if field_name not in output:
            raise LLMAnalysisError(f"Model output missing required field: {field_name}")

    readiness_status = _required_string(output, "readiness_status")
    if readiness_status not in READINESS_STATUSES:
        raise LLMAnalysisError(f"Unsupported readiness_status: {readiness_status}")

    risk_level = _required_string(output, "risk_level")
    if risk_level not in RISK_LEVELS:
        raise LLMAnalysisError(f"Unsupported risk_level: {risk_level}")

    draft_comment = _required_string(output, "draft_comment")
    if contains_secret_like_value(draft_comment):
        raise LLMAnalysisError("Model draft_comment contains a secret-like value.")

    return LLMAnalysis(
        summary=_required_string(output, "summary"),
        work_type=_required_string(output, "work_type"),
        risk_level=risk_level,
        readiness_status=readiness_status,
        missing_information=_string_tuple(output, "missing_information"),
        grooming_questions=_string_tuple(output, "grooming_questions"),
        operational_risk=_string_tuple(output, "operational_risk"),
        security_notes=_string_tuple(output, "security_notes"),
        acceptance_criteria_improvements=_string_tuple(
            output,
            "acceptance_criteria_improvements",
        ),
        recommended_next_action=_required_string(output, "recommended_next_action"),
        draft_comment=draft_comment,
    )


def analysis_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "ticket_readiness_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": list(REQUIRED_OUTPUT_FIELDS),
            "properties": {
                "summary": {"type": "string"},
                "work_type": {"type": "string"},
                "risk_level": {"type": "string", "enum": sorted(RISK_LEVELS)},
                "readiness_status": {"type": "string", "enum": sorted(READINESS_STATUSES)},
                "missing_information": _string_array_schema(),
                "grooming_questions": _string_array_schema(),
                "operational_risk": _string_array_schema(),
                "security_notes": _string_array_schema(),
                "acceptance_criteria_improvements": _string_array_schema(),
                "recommended_next_action": {"type": "string"},
                "draft_comment": {"type": "string"},
            },
        },
    }


def _system_prompt() -> str:
    return (
        "You are a ticket readiness reviewer for cloud infrastructure work. "
        "Return only valid structured output. Do not invent facts, do not include "
        "secrets, and do not select or change Linear issue identifiers."
    )


def _extract_output(response: dict[str, Any]) -> str | dict[str, Any]:
    if "output_text" in response:
        return response["output_text"]

    output = response.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            content = item.get("content") if isinstance(item, dict) else None
            if not isinstance(content, list):
                continue
            for content_item in content:
                if isinstance(content_item, dict) and content_item.get("text"):
                    chunks.append(str(content_item["text"]))
        if chunks:
            return "".join(chunks)

    raise LLMAnalysisError("OpenAI response did not contain model output text.")


def _with_metadata(analysis: LLMAnalysis, response: dict[str, Any]) -> LLMAnalysis:
    metadata = {
        "response_id": response.get("id"),
        "model": response.get("model"),
        "usage": response.get("usage"),
    }
    return LLMAnalysis(
        summary=analysis.summary,
        work_type=analysis.work_type,
        risk_level=analysis.risk_level,
        readiness_status=analysis.readiness_status,
        missing_information=analysis.missing_information,
        grooming_questions=analysis.grooming_questions,
        operational_risk=analysis.operational_risk,
        security_notes=analysis.security_notes,
        acceptance_criteria_improvements=analysis.acceptance_criteria_improvements,
        recommended_next_action=analysis.recommended_next_action,
        draft_comment=analysis.draft_comment,
        model_metadata={key: value for key, value in metadata.items() if value is not None},
    )


def _required_string(output: dict[str, Any], field_name: str) -> str:
    value = output[field_name]
    if not isinstance(value, str) or not value.strip():
        raise LLMAnalysisError(f"Model output field must be a non-empty string: {field_name}")
    return value


def _string_tuple(output: dict[str, Any], field_name: str) -> tuple[str, ...]:
    value = output[field_name]
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, list):
        raise LLMAnalysisError(f"Model output field must be a list or string: {field_name}")
    return tuple(str(item) for item in value if str(item).strip())


def _string_array_schema() -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}}
