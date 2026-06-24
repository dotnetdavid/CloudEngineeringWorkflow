from __future__ import annotations

from ticket_readiness.approvals import ApprovalError
from ticket_readiness.artifacts import ArtifactWriteError
from ticket_readiness.config import ConfigError
from ticket_readiness.errors import TicketReadinessError
from ticket_readiness.linear import LinearReadError
from ticket_readiness.llm_analysis import LLMAnalysisError
from ticket_readiness.writeback import WriteBackError
from ticket_readiness.workflow import WorkflowError


def test_representative_domain_errors_share_operator_safe_base_type():
    domain_errors = (
        ConfigError,
        ArtifactWriteError,
        ApprovalError,
        WorkflowError,
        LinearReadError,
        LLMAnalysisError,
        WriteBackError,
    )

    assert all(issubclass(error_type, TicketReadinessError) for error_type in domain_errors)
