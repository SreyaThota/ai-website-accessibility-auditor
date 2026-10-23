"""Unit tests for touch target size checks (WCAG 2.5.5 / 2.5.8)."""

from auditor.vision.touch_target_checker import TouchTargetChecker
from auditor.models.schemas import BoundingBox, Severity, WCAGLevel


def test_touch_target_severe_under_24px():
    checker = TouchTargetChecker(min_target_aaa=44, min_target_aa=24)
    bbox = BoundingBox(x=10.0, y=20.0, width=16.0, height=16.0)

    issue = checker.evaluate_element_target(".close-btn", "button", bbox)
    assert issue is not None
    assert issue.rule_id == "WCAG_2_5_8_TARGET_SIZE_MINIMUM"
    assert issue.severity == Severity.CRITICAL
    assert issue.level == WCAGLevel.AA


def test_touch_target_moderate_under_44px():
    checker = TouchTargetChecker(min_target_aaa=44, min_target_aa=24)
    bbox = BoundingBox(x=50.0, y=50.0, width=32.0, height=32.0)

    issue = checker.evaluate_element_target(".nav-link", "a", bbox)
    assert issue is not None
    assert issue.rule_id == "WCAG_2_5_5_TARGET_SIZE"
    assert issue.severity == Severity.MODERATE
    assert issue.level == WCAGLevel.AAA


def test_touch_target_compliant_48px():
    checker = TouchTargetChecker(min_target_aaa=44, min_target_aa=24)
    bbox = BoundingBox(x=100.0, y=100.0, width=48.0, height=48.0)

    issue = checker.evaluate_element_target(".submit-btn", "button", bbox)
    assert issue is None


def test_touch_target_asymmetric_dimensions():
    checker = TouchTargetChecker(min_target_aaa=44, min_target_aa=24)
    # Wide button but very thin height (18px)
    bbox = BoundingBox(x=10.0, y=10.0, width=120.0, height=18.0)

    issue = checker.evaluate_element_target(".thin-bar", "button", bbox)
    assert issue is not None
    assert issue.severity == Severity.CRITICAL
