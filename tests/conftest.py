"""Pytest configuration and shared fixtures for AI Website Accessibility Auditor."""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from auditor.models.schemas import BoundingBox, AccessibilityIssue, Severity, WCAGPrinciple, RemediationSnippet


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def demo_dir(project_root: Path) -> Path:
    return project_root / "data" / "demo_sites"


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_bounding_box() -> BoundingBox:
    return BoundingBox(x=10.0, y=20.0, width=120.0, height=35.0)


@pytest.fixture
def sample_issue(sample_bounding_box: BoundingBox) -> AccessibilityIssue:
    return AccessibilityIssue(
        rule_id="DOM_IMG_ALT_MISSING",
        wcag_criterion="1.1.1 Non-text Content",
        principle=WCAGPrinciple.PERCEIVABLE,
        severity=Severity.CRITICAL,
        selector="img.hero-banner",
        description="Image element has no alt attribute.",
        impact="Screen reader users cannot perceive the content or purpose of this image.",
        bounding_box=sample_bounding_box,
        remediation=RemediationSnippet(
            html_before='<img src="/assets/hero.jpg">',
            html_after='<img src="/assets/hero.jpg" alt="Enterprise analytics cloud dashboard preview">',
            explanation="Provide context-specific alt text describing the image content.",
            wcag_reference="https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
        ),
    )
