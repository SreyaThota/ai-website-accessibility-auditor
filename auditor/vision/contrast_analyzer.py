import os
import math
from typing import Tuple, List, Optional, Dict
import numpy as np
from PIL import Image
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

class VisualContrastAnalyzer:
    """
    Mathematical and multi-modal WCAG 2.1 relative luminance and contrast engine.
    Samples pixel clusters from element bounding boxes over screenshots to detect
    low-contrast text over gradients, hero banners, and complex images.
    """

    @staticmethod
    def calculate_relative_luminance(rgb: Tuple[int, int, int]) -> float:
        """
        Calculates relative luminance L per W3C WCAG 2.1 specification:
        L = 0.2126 * R + 0.7152 * G + 0.0722 * B
        """
        r, g, b = [x / 255.0 for x in rgb]

        def gamma_expand(val: float) -> float:
            if val <= 0.03928:
                return val / 12.92
            return math.pow((val + 0.055) / 1.055, 2.4)

        r_lin = gamma_expand(r)
        g_lin = gamma_expand(g)
        b_lin = gamma_expand(b)

        return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

    @classmethod
    def calculate_contrast_ratio(cls, rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
        """
        Computes WCAG contrast ratio between two RGB colors:
        Ratio = (L1 + 0.05) / (L2 + 0.05) where L1 >= L2
        Returns float between 1.0 (identical) and 21.0 (black vs white).
        """
        l1 = cls.calculate_relative_luminance(rgb1)
        l2 = cls.calculate_relative_luminance(rgb2)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        ratio = (lighter + 0.05) / (darker + 0.05)
        return round(ratio, 2)

    def analyze_element_patch(
        self,
        image_path: str,
        bbox: BoundingBox,
        is_large_text: bool = False,
        selector: str = "text-element",
    ) -> Optional[AccessibilityIssue]:
        """
        Samples pixel bounding box from page screenshot, extracts dominant foreground
        and background colors, and evaluates WCAG 1.4.3 (Contrast Minimum).
        """
        if not os.path.exists(image_path) or bbox.width <= 0 or bbox.height <= 0:
            return None

        # Ignore elements positioned entirely off-screen (e.g. skip links or hidden off-canvas elements)
        if (bbox.x + bbox.width <= 0) or (bbox.y + bbox.height <= 0):
            return None

        try:
            with Image.open(image_path) as img:
                img_w, img_h = img.size

                # Ignore elements positioned beyond canvas dimensions
                if bbox.x >= img_w or bbox.y >= img_h:
                    return None

                # Clamp coordinates to image boundaries
                x1 = max(0, int(bbox.x))
                y1 = max(0, int(bbox.y))
                x2 = min(img_w, int(bbox.x + bbox.width))
                y2 = min(img_h, int(bbox.y + bbox.height))

                if x2 - x1 < 2 or y2 - y1 < 2:
                    return None

                crop = img.crop((x1, y1, x2, y2)).convert("RGB")
                pixels = np.array(crop).reshape(-1, 3)

                # Segment pixels into foreground (text) and background via luminance percentile
                luminances = np.array([self.calculate_relative_luminance(tuple(p)) for p in pixels])

                # If the patch has virtually no color/luminance variation (solid color or no rendered text),
                # skip visual text contrast evaluation to avoid false positives on non-text elements
                if float(np.max(luminances) - np.min(luminances)) < 0.05:
                    return None

                sorted_indices = np.argsort(luminances)

                # Cluster dark pixels vs light pixels using top/bottom 5% percentile
                # to prevent text glyphs from being diluted by large background padding
                k = max(1, int(len(pixels) * 0.05))
                dark_pixels = pixels[sorted_indices[:k]]
                light_pixels = pixels[sorted_indices[-k:]]

                dark_mean = tuple(np.mean(dark_pixels, axis=0).astype(int))
                light_mean = tuple(np.mean(light_pixels, axis=0).astype(int))

                ratio = self.calculate_contrast_ratio(light_mean, dark_mean)
                required_ratio = settings.MIN_LARGE_CONTRAST if is_large_text else settings.MIN_NORMAL_CONTRAST

                if ratio < required_ratio:
                    severity = Severity.CRITICAL if ratio < 2.5 else Severity.MAJOR
                    text_type = "Large text (>=18pt or >=14pt bold)" if is_large_text else "Normal body text"

                    return AccessibilityIssue(
                        id=f"VISUAL_1_4_3_CONTRAST_{abs(hash(selector)) % 10000}",
                        rule_id="WCAG_1_4_3_CONTRAST_MINIMUM",
                        principle=WCAGPrinciple.PERCEIVABLE,
                        level=WCAGLevel.AA,
                        severity=severity,
                        element_selector=selector,
                        element_tag="span",
                        description=f"Insufficient visual text contrast ratio ({ratio}:1 vs required {required_ratio}:1).",
                        failure_summary=(
                            f"{text_type} has measured contrast ratio of {ratio}:1, failing WCAG AA minimum threshold of {required_ratio}:1. "
                            f"Sampled colors: Foreground rgb{dark_mean} vs Background rgb{light_mean}."
                        ),
                        bounding_box=bbox,
                        remediation=RemediationSnippet(
                            current_code=f"color: rgb{dark_mean}; background-color: rgb{light_mean};",
                            recommended_code="color: #0f172a; background-color: #ffffff; /* Contrast ratio 19.5:1 (Passes AAA) */",
                            explanation=(
                                f"Increase contrast between text and background to at least {required_ratio}:1. "
                                "For text on images or gradients, add a solid or semi-transparent background overlay."
                            ),
                            wcag_criterion="1.4.3 Contrast (Minimum)",
                            wcag_url="https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html",
                        ),
                    )

        except Exception as e:
            logger.warning(f"Error analyzing visual contrast for {selector}: {e}")

        return None

# Singleton instance
contrast_analyzer = VisualContrastAnalyzer()
