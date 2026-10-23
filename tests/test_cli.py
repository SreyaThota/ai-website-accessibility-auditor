"""Unit tests for the CLI entrypoint."""

import pytest
from unittest.mock import patch
from cli import parse_args, main_async
from auditor.models.schemas import AuditReport, AuditSummary


def test_cli_parse_args_preset():
    with patch("sys.argv", ["cli.py", "--preset", "inaccessible_portal"]):
        args = parse_args()
        assert args.preset == "inaccessible_portal"
        assert args.url is None
        assert not args.no_vision
        assert not args.no_ai_alt


def test_cli_parse_args_url_flags():
    with patch("sys.argv", ["cli.py", "--url", "https://example.com", "--no-vision", "--no-ai-alt"]):
        args = parse_args()
        assert args.url == "https://example.com"
        assert args.preset is None
        assert args.no_vision is True
        assert args.no_ai_alt is True


@pytest.mark.asyncio
async def test_cli_main_async_execution():
    mock_summary = AuditSummary(
        url="preset:compliant_portal",
        overall_score=95.0,
        wcag_level_conformance="COMPLIANT_AA",
        eea_compliance_status="PASS - Meets EAA Mandates (EN 301 549)",
        perceivable_score=95.0,
        operable_score=95.0,
        understandable_score=100.0,
        robust_score=100.0,
        total_issues=0,
        critical_issues=0,
        major_issues=0,
        moderate_issues=0,
        minor_issues=0,
        duration_seconds=1.2,
    )
    mock_report = AuditReport(
        job_id="test_cli_job",
        url="preset:compliant_portal",
        summary=mock_summary,
        issues=[],
    )

    with patch("sys.argv", ["cli.py", "--preset", "compliant_portal"]):
        with patch("auditor.core.engine.engine.run_audit", return_value=mock_report):
            exit_code = await main_async()
            assert exit_code == 0
