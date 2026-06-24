from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ticket_readiness.linear import LinearIssue


@dataclass(frozen=True)
class DeterministicFinding:
    dimension: str
    status: str
    message: str
    evidence: tuple[str, ...] = ()
    required: bool = True

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["evidence"] = list(self.evidence)
        return payload


@dataclass(frozen=True)
class RiskFlag:
    level: str
    code: str
    message: str
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["evidence"] = list(self.evidence)
        return payload


class ReadinessConfigError(ValueError):
    """Raised when readiness customization is invalid."""


@dataclass(frozen=True)
class CustomCheck:
    dimension: str
    patterns: tuple[str, ...]
    present_message: str
    missing_message: str
    required: bool = True


@dataclass(frozen=True)
class DeterministicReadinessResult:
    issue_id: str
    work_type: str
    findings: tuple[DeterministicFinding, ...]
    risk_flags: tuple[RiskFlag, ...]
    trivially_incomplete: bool

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "work_type": self.work_type,
            "findings": [finding.to_dict() for finding in self.findings],
            "risk_flags": [flag.to_dict() for flag in self.risk_flags],
            "trivially_incomplete": self.trivially_incomplete,
        }


def evaluate_issue(
    issue: LinearIssue,
    *,
    custom_checks: Iterable[CustomCheck] = (),
) -> DeterministicReadinessResult:
    text = _issue_text(issue)
    risk_flags = tuple(_risk_flags(text))
    work_type = _work_type(text, risk_flags)
    lighter_requirements = work_type in {"documentation_only", "planning_only"}
    security_sensitive = _has_any_risk(
        risk_flags,
        {"production", "iam", "eks_admin_access", "security_group_change", "broad_network_access"},
    )
    infrastructure_change = work_type in {"infrastructure_change", "access_change", "database_change"}

    findings = [
        _presence("title", bool(issue.title.strip()), "Title exists.", "Title is missing."),
        _presence(
            "description",
            len(issue.description.strip()) >= 20,
            "Description has useful detail.",
            "Description is missing or too thin.",
        ),
        _presence(
            "priority",
            issue.priority.value is not None,
            "Priority is set.",
            "Priority is missing.",
        ),
        _presence(
            "estimate",
            issue.estimate is not None,
            "Estimate is set.",
            "Estimate is missing.",
        ),
        _signal(
            "outcome_clarity",
            text,
            (r"\bso that\b", r"\bin order to\b", r"\bgoal\b", r"\boutcome\b"),
            "Outcome signal is present.",
            "Desired outcome is not explicit.",
        ),
        _signal(
            "scope_boundaries",
            text,
            (r"\bscope\b", r"\bin scope\b", r"\bout of scope\b", r"\bonly\b", r"\bexclude"),
            "Scope boundary signal is present.",
            "Scope boundaries are not explicit.",
            required=False,
        ),
        _signal(
            "acceptance_criteria",
            text,
            (
                r"\bacceptance criteria\b",
                r"\bsuccess criteria\b",
                r"\bdefinition of done\b",
                r"\bdone when\b",
            ),
            "Acceptance criteria signal is present.",
            "Acceptance criteria are missing.",
        ),
        _conditional_signal(
            "environment_blast_radius",
            text,
            (
                r"\bproduction\b",
                r"\bprod\b",
                r"\bsandbox\b",
                r"\bstaging\b",
                r"\baccount\b",
                r"\bregion\b",
                r"\bus-[a-z]+-\d\b",
                r"\bvpc\b",
                r"\beks\b",
                r"\brds\b",
                r"\bs3\b",
                r"\bsubnet",
                r"\broute table",
            ),
            required=not lighter_requirements and infrastructure_change,
            present_message="Environment or blast-radius signal is present.",
            missing_message="Environment, account, region, service, or blast radius is missing.",
        ),
        _conditional_signal(
            "rollback_recovery",
            text,
            (r"\brollback\b", r"\bbackout\b", r"\brevert\b", r"\brestore\b", r"\brecovery\b"),
            required=not lighter_requirements and infrastructure_change,
            present_message="Rollback or recovery signal is present.",
            missing_message="Rollback or recovery path is missing.",
        ),
        _conditional_signal(
            "security_impact",
            text,
            (
                r"\bsecurity review\b",
                r"\bleast privilege\b",
                r"\bsecurity approval\b",
                r"\bno public ingress\b",
                r"\bno iam\b",
                r"\bno secrets\b",
                r"\baccess review\b",
                r"\bguardrail",
            ),
            required=not lighter_requirements and security_sensitive,
            present_message="Security impact signal is present.",
            missing_message="Security review or access-risk signal is missing.",
        ),
        _signal(
            "observability_validation",
            text,
            (
                r"\bvalidation\b",
                r"\bvalidate\b",
                r"\bverify\b",
                r"\btest\b",
                r"\bsmoke\b",
                r"\bmonitor\b",
                r"\bmetric",
                r"\bterraform plan\b",
            ),
            "Validation signal is present.",
            "Validation signal is missing.",
        ),
        _signal(
            "dependencies_ownership",
            text,
            (
                r"\bowner\b",
                r"\bapprover\b",
                r"\bdependency\b",
                r"\bdepends\b",
                r"\bblocked\b",
                r"\bteam\b",
                r"\bstakeholder\b",
            ),
            "Dependency or ownership signal is present.",
            "Dependency or ownership signal is missing.",
            required=False,
        ),
    ]
    findings.extend(_custom_findings(text, custom_checks))

    trivially_incomplete = not issue.title.strip() or len(issue.description.strip()) < 20

    return DeterministicReadinessResult(
        issue_id=issue.identifier,
        work_type=work_type,
        findings=tuple(findings),
        risk_flags=risk_flags,
        trivially_incomplete=trivially_incomplete,
    )


def load_custom_checks(config: dict[str, Any]) -> tuple[CustomCheck, ...]:
    readiness_config = config.get("readiness")
    if readiness_config is None:
        return ()
    if not isinstance(readiness_config, dict):
        raise ReadinessConfigError("readiness config must be a mapping.")

    raw_checks = readiness_config.get("custom_checks", [])
    if raw_checks is None:
        return ()
    if not isinstance(raw_checks, list):
        raise ReadinessConfigError("readiness.custom_checks must be a list.")

    return tuple(_custom_check_from_config(index, raw_check) for index, raw_check in enumerate(raw_checks))


def _presence(
    dimension: str,
    present: bool,
    present_message: str,
    missing_message: str,
    *,
    required: bool = True,
) -> DeterministicFinding:
    return DeterministicFinding(
        dimension=dimension,
        status="present" if present else "missing",
        message=present_message if present else missing_message,
        required=required,
    )


def _signal(
    dimension: str,
    text: str,
    patterns: Iterable[str],
    present_message: str,
    missing_message: str,
    *,
    required: bool = True,
) -> DeterministicFinding:
    evidence = _evidence(text, patterns)
    return DeterministicFinding(
        dimension=dimension,
        status="present" if evidence else "missing",
        message=present_message if evidence else missing_message,
        evidence=evidence,
        required=required,
    )


def _conditional_signal(
    dimension: str,
    text: str,
    patterns: Iterable[str],
    *,
    required: bool,
    present_message: str,
    missing_message: str,
) -> DeterministicFinding:
    if not required:
        return DeterministicFinding(
            dimension=dimension,
            status="not_applicable",
            message="Dimension is not required for this work type.",
            required=False,
        )
    return _signal(dimension, text, patterns, present_message, missing_message)


def _custom_findings(
    text: str,
    custom_checks: Iterable[CustomCheck],
) -> list[DeterministicFinding]:
    return [
        _signal(
            check.dimension,
            text,
            check.patterns,
            check.present_message,
            check.missing_message,
            required=check.required,
        )
        for check in custom_checks
    ]


def _risk_flags(text: str) -> list[RiskFlag]:
    checks = [
        ("high", "production", "Production impact signal.", (r"\bproduction\b", r"\bprod\b")),
        ("high", "iam", "IAM or privileged access signal.", (r"\biam\b", r"\bpermission", r"\bpolicy\b", r"\brole\b")),
        ("high", "eks_admin_access", "EKS admin access signal.", (r"\beks admin\b", r"\bcluster-admin\b", r"\bsystem:masters\b")),
        ("high", "database_reboot", "Database reboot or data-path signal.", (r"\bdatabase reboot\b", r"\bdb reboot\b", r"\brds reboot\b", r"\breboot .*database\b")),
        ("high", "security_group_change", "Security group or ingress signal.", (r"\bsecurity group\b", r"\bsg ingress\b", r"\bingress\b", r"\begress\b")),
        ("high", "broad_network_access", "Broad network access signal.", (r"0\.0\.0\.0/0", r"\ball traffic\b", r"\bany source\b", r"\bbroad network\b")),
        ("medium", "cost_anomaly", "Cost anomaly signal.", (r"\bcost\b", r"\bspend\b", r"\banomaly\b", r"\bbudget\b")),
        ("medium", "terraform_drift", "Terraform drift signal.", (r"\bterraform drift\b", r"\bdrift\b")),
        ("medium", "observability_module", "Observability module signal.", (r"\bobservability\b", r"\btelemetry\b", r"\bdashboard\b")),
        ("medium", "vpc_endpoint", "VPC endpoint or route-table signal.", (r"\bvpc endpoint\b", r"\broute table\b")),
        ("low", "documentation_only", "Documentation-only signal.", (r"\bdocumentation\b", r"\bdocs\b", r"\breadme\b", r"\brunbook\b")),
        ("low", "planning_only", "Planning-only signal.", (r"\bplanning\b", r"\bplan backlog\b", r"\bdiscovery\b", r"\bdesign\b", r"\bgrooming\b")),
    ]

    flags: list[RiskFlag] = []
    for level, code, message, patterns in checks:
        evidence = _risk_evidence(text, patterns)
        if evidence:
            flags.append(RiskFlag(level=level, code=code, message=message, evidence=evidence))
    return flags


def _work_type(text: str, risk_flags: tuple[RiskFlag, ...]) -> str:
    risk_codes = {flag.code for flag in risk_flags}
    if "documentation_only" in risk_codes and not risk_codes.intersection(_HIGH_INFRA_RISKS):
        return "documentation_only"
    if "planning_only" in risk_codes and not risk_codes.intersection(_HIGH_INFRA_RISKS):
        return "planning_only"
    if "database_reboot" in risk_codes:
        return "database_change"
    if risk_codes.intersection({"iam", "eks_admin_access"}):
        return "access_change"
    if risk_codes.intersection({"vpc_endpoint", "security_group_change", "broad_network_access"}):
        return "infrastructure_change"
    if _evidence(
        text,
        (
            r"\baws\b",
            r"\bcloud\b",
            r"\bterraform\b",
            r"\bvpc\b",
            r"\bs3\b",
            r"\beks\b",
            r"\brds\b",
            r"\blambda\b",
            r"\bsubnet",
        ),
    ):
        return "infrastructure_change"
    return "general"


def _has_any_risk(risk_flags: tuple[RiskFlag, ...], codes: set[str]) -> bool:
    return any(flag.code in codes for flag in risk_flags)


def _issue_text(issue: LinearIssue) -> str:
    return f"{issue.title}\n{issue.description}".lower()


def _evidence(text: str, patterns: Iterable[str]) -> tuple[str, ...]:
    found: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            found.append(match.group(0))
    return tuple(found)


def _risk_evidence(text: str, patterns: Iterable[str]) -> tuple[str, ...]:
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            if not _is_negated(text, match.start()):
                found.append(match.group(0))
                break
    return tuple(found)


def _is_negated(text: str, match_start: int) -> bool:
    window = text[max(0, match_start - 32) : match_start]
    return re.search(r"\b(no|not|without)\s+(?:[a-z0-9-]+\s+){0,3}$", window) is not None


_HIGH_INFRA_RISKS = {
    "production",
    "iam",
    "eks_admin_access",
    "database_reboot",
    "security_group_change",
    "broad_network_access",
}


def _custom_check_from_config(index: int, raw_check: Any) -> CustomCheck:
    if not isinstance(raw_check, dict):
        raise ReadinessConfigError(f"readiness.custom_checks[{index}] must be a mapping.")

    dimension = _required_config_string(raw_check, "dimension", index)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", dimension):
        raise ReadinessConfigError(
            f"readiness.custom_checks[{index}].dimension must use lowercase letters, numbers, and underscores."
        )

    patterns = raw_check.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        raise ReadinessConfigError(f"readiness.custom_checks[{index}].patterns must be a non-empty list.")
    pattern_values = tuple(_pattern_string(pattern, index) for pattern in patterns)

    for pattern in pattern_values:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ReadinessConfigError(
                f"readiness.custom_checks[{index}] contains invalid regex: {pattern}"
            ) from exc

    required = raw_check.get("required", True)
    if not isinstance(required, bool):
        raise ReadinessConfigError(f"readiness.custom_checks[{index}].required must be true or false.")

    return CustomCheck(
        dimension=dimension,
        patterns=pattern_values,
        present_message=str(
            raw_check.get("present_message") or f"{dimension} signal is present."
        ),
        missing_message=str(raw_check.get("missing_message") or f"{dimension} signal is missing."),
        required=required,
    )


def _required_config_string(raw_check: dict[str, Any], key: str, index: int) -> str:
    value = raw_check.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ReadinessConfigError(f"readiness.custom_checks[{index}].{key} must be a non-empty string.")
    return value.strip()


def _pattern_string(pattern: Any, index: int) -> str:
    if not isinstance(pattern, str) or not pattern.strip():
        raise ReadinessConfigError(
            f"readiness.custom_checks[{index}].patterns entries must be non-empty strings."
        )
    return pattern
