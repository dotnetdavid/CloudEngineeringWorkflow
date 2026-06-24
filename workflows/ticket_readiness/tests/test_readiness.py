from __future__ import annotations

from ticket_readiness.linear import LinearIssue, LinearPriority
from ticket_readiness.readiness import CustomCheck, evaluate_issue


def test_readyish_infrastructure_ticket_has_expected_signals():
    issue = _issue(
        "ASG-40",
        "Add S3 VPC endpoint for private artifact bucket access",
        """
        Create a gateway VPC endpoint for S3 in the sandbox account, us-east-1,
        so that private build workers can reach the artifact bucket without NAT.

        Scope: sandbox VPC route tables only.

        Acceptance Criteria:
        - Endpoint is created by Terraform.
        - Route tables are updated for private subnets.
        - Existing bucket access still works.

        Rollback: revert the Terraform change and remove endpoint routes.
        Validation: run terraform plan/apply in sandbox and verify S3 access
        from a private worker.
        Security: no public ingress and no IAM policy changes.
        Owner: platform team.
        """,
        priority=2,
        estimate=3,
    )

    result = evaluate_issue(issue)

    assert result.work_type == "infrastructure_change"
    assert not result.trivially_incomplete
    assert _missing_dimensions(result) == set()
    assert _risk_codes(result) == {"vpc_endpoint"}


def test_vague_production_ticket_is_trivially_incomplete_and_high_risk():
    issue = _issue(
        "ASG-41",
        "Fix production networking",
        "",
        priority=None,
        estimate=None,
    )

    result = evaluate_issue(issue)

    assert result.trivially_incomplete
    assert {"description", "priority", "estimate", "acceptance_criteria"}.issubset(
        _missing_dimensions(result)
    )
    assert "production" in _risk_codes(result)


def test_security_sensitive_ticket_requires_security_and_rollback_signals():
    issue = _issue(
        "ASG-42",
        "Grant EKS admin access for incident responders",
        """
        Add IAM permissions so incident responders can use cluster-admin access
        in production EKS.

        Acceptance Criteria:
        - Responders can authenticate to the cluster.
        Validation: verify access with kubectl auth can-i.
        """,
        priority=1,
        estimate=2,
    )

    result = evaluate_issue(issue)

    assert {"iam", "eks_admin_access", "production"}.issubset(_risk_codes(result))
    assert {"rollback_recovery", "security_impact"}.issubset(_missing_dimensions(result))


def test_planning_ticket_uses_lighter_requirements():
    issue = _issue(
        "ASG-45",
        "Plan backlog grooming for cloud workflow rollout",
        """
        Create a planning agenda and identify open questions for backlog grooming.

        Acceptance Criteria:
        - Grooming agenda is drafted.
        - Unknowns are captured as follow-up tickets.
        Validation: review agenda with the platform owner.
        """,
        priority=3,
        estimate=1,
    )

    result = evaluate_issue(issue)

    assert result.work_type == "planning_only"
    assert "planning_only" in _risk_codes(result)
    assert "rollback_recovery" not in _missing_dimensions(result)
    assert "security_impact" not in _missing_dimensions(result)


def test_high_risk_flags_include_database_and_broad_network_access():
    issue = _issue(
        "ASG-48",
        "Reboot production database and open security group ingress",
        """
        Reboot the production RDS database and temporarily allow 0.0.0.0/0
        ingress to test connectivity.

        Acceptance Criteria:
        - Database is reachable after reboot.
        Validation: run application smoke tests.
        Owner: database team.
        """,
        priority=1,
        estimate=5,
    )

    result = evaluate_issue(issue)

    assert {"production", "database_reboot", "security_group_change", "broad_network_access"}.issubset(
        _risk_codes(result)
    )
    assert "rollback_recovery" in _missing_dimensions(result)


def test_custom_required_check_adds_missing_dimension_without_disabling_defaults():
    issue = _issue(
        "ASG-49",
        "Deploy sandbox route table update",
        """
        Update the sandbox route table so that private workers use the S3 VPC
        endpoint.

        Acceptance Criteria:
        - Terraform updates the target route table.
        Validation: verify S3 access from a private worker.
        Rollback: revert the Terraform change.
        """,
        priority=2,
        estimate=3,
    )

    result = evaluate_issue(
        issue,
        custom_checks=[
            CustomCheck(
                dimension="change_window",
                patterns=(r"\bchange window\b", r"\bmaintenance window\b"),
                present_message="Change window signal is present.",
                missing_message="Change window is missing.",
                required=True,
            )
        ],
    )

    assert "acceptance_criteria" not in _missing_dimensions(result)
    change_window = next(
        finding for finding in result.findings if finding.dimension == "change_window"
    )
    assert change_window.status == "missing"
    assert change_window.required
    assert change_window.message == "Change window is missing."


def test_custom_optional_check_records_present_signal_when_available():
    issue = _issue(
        "ASG-50",
        "Deploy sandbox route table update during maintenance window",
        """
        Update the sandbox route table during the maintenance window so that
        private workers use the S3 VPC endpoint.

        Acceptance Criteria:
        - Terraform updates the target route table.
        Validation: verify S3 access from a private worker.
        Rollback: revert the Terraform change.
        """,
        priority=2,
        estimate=3,
    )

    result = evaluate_issue(
        issue,
        custom_checks=[
            CustomCheck(
                dimension="change_window",
                patterns=(r"\bchange window\b", r"\bmaintenance window\b"),
                present_message="Change window signal is present.",
                missing_message="Change window is missing.",
                required=False,
            )
        ],
    )

    change_window = next(
        finding for finding in result.findings if finding.dimension == "change_window"
    )
    assert change_window.status == "present"
    assert not change_window.required
    assert change_window.evidence == ("maintenance window",)


def _issue(
    identifier: str,
    title: str,
    description: str,
    *,
    priority: int | None,
    estimate: int | None,
) -> LinearIssue:
    return LinearIssue(
        identifier=identifier,
        title=title,
        description=description.strip(),
        priority=LinearPriority(value=priority),
        estimate=estimate,
    )


def _missing_dimensions(result) -> set[str]:
    return {finding.dimension for finding in result.findings if finding.status == "missing"}


def _risk_codes(result) -> set[str]:
    return {flag.code for flag in result.risk_flags}
