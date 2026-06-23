from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from ticket_readiness.workflow import (
    post_approved,
    run_analysis,
    summarize_run,
    validate_approvals,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ticket-readiness",
        description="Evaluate Linear issue readiness and produce review artifacts.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/linear-sandbox.yaml"),
        help="Path to the workflow configuration YAML file.",
    )

    subcommands = parser.add_subparsers(dest="command", required=True)

    run_analysis = subcommands.add_parser(
        "run-analysis",
        help="Analyze configured Linear issues and write readiness reports.",
    )
    run_analysis.add_argument("--fixture-data", type=Path)
    run_analysis.add_argument("--mock-llm", action="store_true")
    run_analysis.set_defaults(handler=_run_analysis)

    validate_approvals = subcommands.add_parser(
        "validate-approvals",
        help="Validate that generated write-back comments have human approval.",
    )
    validate_approvals.add_argument("--run", required=True)
    validate_approvals.set_defaults(handler=_validate_approvals)

    post_approved = subcommands.add_parser(
        "post-approved",
        help="Post approved readiness comments back to Linear.",
    )
    post_approved.add_argument("--run", required=True)
    post_approved.add_argument("--issue-id", required=True)
    post_approved.set_defaults(handler=_post_approved)

    summarize_run = subcommands.add_parser(
        "summarize-run",
        help="Create a run summary from generated reports and write-back results.",
    )
    summarize_run.add_argument("--run", required=True)
    summarize_run.set_defaults(handler=_summarize_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def _run_analysis(args: argparse.Namespace) -> int:
    run_id = run_analysis(
        config_path=args.config,
        fixture_data=args.fixture_data,
        mock_llm=args.mock_llm,
    )
    print(f"Run created: {run_id}")
    return 0


def _validate_approvals(args: argparse.Namespace) -> int:
    valid = validate_approvals(config_path=args.config, run_id=args.run)
    print("Approvals valid." if valid else "One or more approvals are invalid.")
    return 0 if valid else 1


def _post_approved(args: argparse.Namespace) -> int:
    posted = post_approved(config_path=args.config, run_id=args.run, issue_id=args.issue_id)
    print("Approved comment posted." if posted else "Approved comment was not posted.")
    return 0 if posted else 1


def _summarize_run(args: argparse.Namespace) -> int:
    summary_path = summarize_run(config_path=args.config, run_id=args.run)
    print(f"Summary written: {summary_path}")
    return 0
