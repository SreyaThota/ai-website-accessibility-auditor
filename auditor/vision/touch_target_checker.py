from typing import List, Dict, Optional
from auditor.models.schemas import (
    AccessibilityIssue,
    WCAGPrinciple,
    WCAGLevel,
    Severity,
    RemediationSnippet,
    BoundingBox,
)
from auditor.core.config import settings
from auditor.core.logging import logger

class TouchTargetChecker:
    """
    Evaluates interactive controls against WCAG 2.5.5 (Target Size - Level AAA: 44x44px)
    and WCAG 2.5.8 (Target Size Minimum - Level AA: 24x24px).
    Prevents motor impairment barriers and touch screen input errors.
    """

    def __init__(
        self,
        min_target_aaa: int = settings.MIN_TOUCH_TARGET_SIZE,
        min_target_aa: int = settings.MIN_TOUCH_TARGET_AA,
    ):
        self.min_target_aaa = min_target_aaa
        self.min_target_aa = min_target_aa

    def evaluate_element_target(
        self,
        selector: str,
        tag: str,
        bbox: BoundingBox,
        is_inline: bool = False,
    ) -> Optional[AccessibilityIssue]:
        """Checks if an interactive element has sufficient touch target dimensions."""
        if is_inline:
            return None  # WCAG 2.5.8 Exception: Target is inline within a block of text

        w = round(bbox.width, 1)
        h = round(bbox.height, 1)

        # Under 24x24 px is a Level AA failure under WCAG 2.2 / European standard EN 301 549
        if w < self.min_target_aa or h < self.min_target_aa:
            return AccessibilityIssue(
                id=f"TARGET_2_5_8_UNDER_24PX_{abs(hash(selector)) % 10000}",
                rule_id="WCAG_2_5_8_TARGET_SIZE_MINIMUM",
                principle=WCAGPrinciple.OPERABLE,
                level=WCAGLevel.AA,
                severity=Severity.CRITICAL,
                element_selector=selector,
                element_tag=tag,
                description=f"Interactive control is undersized ({w}x{h}px < required {self.min_target_aa}x{self.min_target_aa}px minimum).",
                failure_summary=(
                    f"Element measures {w}px wide by {h}px high. Interactive targets smaller than {self.min_target_aa}px "
                    "cannot be reliably activated by users with tremors, motor disabilities, or on mobile devices."
                ),
                bounding_box=bbox,
                remediation=RemediationSnippet(
                    current_code=f"<{tag} style=\"width: {w}px; height: {h}px;\">...</{tag}>",
                    recommended_code=f"min-width: {self.min_target_aaa}px;\nmin-height: {self.min_target_aaa}px;\npadding: 10px;\ndisplay: inline-flex;\nalign-items: center;\njustify-content: center;",
                    explanation=f"Increase the clickable touch area by adding CSS padding or setting min-width and min-height to at least {self.min_target_aaa}px.",
                    wcag_criterion="2.5.8 Target Size (Minimum) / 2.5.5 Target Size",
                    wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/target-size.html",
                ),
            )

        # Under 44x44 px is a Level AAA violation and WCAG 2.1 best practice
        if w < self.min_target_aaa or h < self.min_target_aaa:
            return AccessibilityIssue(
                id=f"TARGET_2_5_5_UNDER_44PX_{abs(hash(selector)) % 10000}",
                rule_id="WCAG_2_5_5_TARGET_SIZE",
                principle=WCAGPrinciple.OPERABLE,
                level=WCAGLevel.AAA,
                severity=Severity.MODERATE,
                element_selector=selector,
                element_tag=tag,
                description=f"Interactive control does not meet optimal 44x44px touch target recommendation ({w}x{h}px).",
                failure_summary=f"Element measures {w}x{h}px. Recommended standard target size is at least {self.min_target_aaa}x{self.min_target_aaa} CSS pixels.",
                bounding_box=bbox,
                remediation=RemediationSnippet(
                    current_code=f"<{tag} style=\"width: {w}px; height: {h}px;\">...</{tag}>",
                    recommended_code=f"min-width: {self.min_target_aaa}px;\nmin-height: {self.min_target_aaa}px;\npadding: 8px;",
                    explanation=f"Expand target dimensions to at least {self.min_target_aaa}px by increasing touch padding.",
                    wcag_criterion="2.5.5 Target Size",
                    wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/target-size.html",
                ),
            )

        return None

# Singleton instance
touch_target_checker = TouchTargetChecker()
