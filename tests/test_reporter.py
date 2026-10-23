"""Unit tests for accessibility audit reporting engine and score calculation."""

import os
import json
import pytest
from pathlib import Path
from auditor.reporter.report_generator import AuditReportGenerator
from auditor.models.schemas import (
    AccessibilityIssue,
    AuditReport,
    WCAGPrinciple,
    WCAGLevel,
    Severity,
    RemediationSnippet,
)


def test_perfect_score_calculation():
    report = AuditReportGenerator.build_report(
        job_id="test_job_perfect",
        url="https://compliant.example.edu",
        issues=[],
        duration_seconds=1.25,
    )
    assert report.summary.overall_score == 100.0
    assert report.summary.wcag_level_conformance == "COMPLIANT_AA"
    assert "PASS" in report.summary.eea_compliance_status
    assert report.summary.critical_issues == 0
    assert report.summary.perceivable_score == 100.0


def test_weighted_deduction_calculation():
    sample_issues = [
        AccessibilityIssue(
            id="CRIT_1",
            rule_id="WCAG_1_1_1",
            principle=WCAGPrinciple.PERCEIVABLE,
            level=WCAGLevel.A,
            severity=Severity.CRITICAL,
            element_selector="img",
            element_tag="img",
            description="Missing alt",
            failure_summary="Fail",
            remediation=RemediationSnippet(
                current_code="<img src=''>",
                recommended_code="<img src='' alt='desc'>",
                explanation="Fix",
                wcag_criterion="1.1.1",
                wcag_url="http://example.com",
            ),
        ),
        AccessibilityIssue(
            id="MAJ_1",
            rule_id="WCAG_2_4_2",
            principle=WCAGPrinciple.OPERABLE,
            level=WCAGLevel.A,
            severity=Severity.MAJOR,
            element_selector="title",
            element_tag="title",
            description="Missing title",
            failure_summary="Fail",
            remediation=RemediationSnippet(
                current_code="<head>",
                recommended_code="<title>Page</title>",
                explanation="Fix",
                wcag_criterion="2.4.2",
                wcag_url="http://example.com",
            ),
        ),
    ]

    report = AuditReportGenerator.build_report(
        job_id="test_job_deduct",
        url="https://inaccessible.example.edu",
        issues=sample_issues,
        duration_seconds=2.1,
    )

    # 100 - (15.0 for critical + 8.0 for major) = 77.0
    assert report.summary.overall_score == 77.0
    assert report.summary.critical_issues == 1
    assert report.summary.major_issues == 1
    assert "FAIL" in report.summary.eea_compliance_status
    assert report.summary.wcag_level_conformance == "NON_COMPLIANT"


def test_artifacts_saved_to_disk(tmp_path):
    report = AuditReportGenerator.build_report(
        job_id="test_artifacts_disk",
        url="https://demo.example.edu",
        issues=[],
        duration_seconds=0.5,
    )

    json_path, html_path = AuditReportGenerator.save_artifacts(report)

    assert os.path.exists(json_path)
    assert os.path.exists(html_path)

    # Verify JSON content
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["job_id"] == "test_artifacts_disk"
        assert data["summary"]["overall_score"] == 100.0

    # Verify HTML content
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "AI Website Accessibility Audit Report" in content
        assert "https://demo.example.edu" in content
