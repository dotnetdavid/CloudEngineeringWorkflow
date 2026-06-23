from ticket_readiness.cli import build_parser


def test_cli_help_includes_core_commands():
    parser = build_parser()

    help_text = parser.format_help()

    assert "run-analysis" in help_text
    assert "validate-approvals" in help_text
    assert "post-approved" in help_text
    assert "summarize-run" in help_text

