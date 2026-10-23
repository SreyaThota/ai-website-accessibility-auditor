"""Integration tests for master AccessibilityAuditEngine orchestrator."""

import pytest
from auditor.core.engine import engine
from auditor.models.schemas import Severity


@pytest.mark.asyncio
async def test_engine_run_audit_on_inaccessible_portal():
    report = await engine.run_audit(
        url="preset:inaccessible_portal",
        check_visual_contrast=False,
        generate_ai_alt_text=True,
        check_touch_targets=True,
    )

    assert report is not None
    assert report.url == "preset:inaccessible_portal"
    assert len(report.issues) > 0
    assert report.summary.critical_issues > 0

    # Verify AI alt text was enriched for missing alt image issues
    alt_issues = [i for i in report.issues if i.rule_id == "WCAG_1_1_1_NON_TEXT_CONTENT"]
    assert len(alt_issues) > 0
    assert any("AI Vision Model Proposed Alt-Text" in i.remediation.explanation for i in alt_issues)

    # Verify cache retrieval
    cached = engine.get_report(report.job_id)
    assert cached is not None
    assert cached.job_id == report.job_id


@pytest.mark.asyncio
async def test_engine_run_audit_on_compliant_portal():
    report = await engine.run_audit(
        url="preset:compliant_portal",
        check_visual_contrast=False,
        generate_ai_alt_text=False,
        check_touch_targets=True,
    )

    assert report is not None
    assert report.summary.critical_issues == 0
    assert report.summary.overall_score >= 80.0
    assert "PASS" in report.summary.eea_compliance_status
