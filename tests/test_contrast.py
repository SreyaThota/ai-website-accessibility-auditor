"""Unit tests for visual contrast analysis and WCAG 1.4.3 mathematical accuracy."""

import os
import tempfile
import pytest
from PIL import Image, ImageDraw
from auditor.vision.contrast_analyzer import VisualContrastAnalyzer
from auditor.models.schemas import BoundingBox, Severity


def test_relative_luminance_extremes():
    black = (0, 0, 0)
    white = (255, 255, 255)

    lum_black = VisualContrastAnalyzer.calculate_relative_luminance(black)
    lum_white = VisualContrastAnalyzer.calculate_relative_luminance(white)

    assert lum_black == pytest.approx(0.0, abs=1e-5)
    assert lum_white == pytest.approx(1.0, abs=1e-5)


def test_contrast_ratio_black_and_white():
    black = (0, 0, 0)
    white = (255, 255, 255)

    ratio = VisualContrastAnalyzer.calculate_contrast_ratio(black, white)
    assert ratio == 21.0


def test_contrast_ratio_identical_colors():
    color = (120, 80, 200)
    ratio = VisualContrastAnalyzer.calculate_contrast_ratio(color, color)
    assert ratio == 1.0


def test_contrast_ratio_standard_pairs():
    # Dark charcoal on white
    dark = (33, 37, 41)
    white = (255, 255, 255)
    ratio_pass = VisualContrastAnalyzer.calculate_contrast_ratio(dark, white)
    assert ratio_pass >= 12.0  # Well above 4.5:1

    # Light grey on white (fails AA)
    light_grey = (200, 200, 200)
    ratio_fail = VisualContrastAnalyzer.calculate_contrast_ratio(light_grey, white)
    assert ratio_fail < 3.0  # Fails both normal and large text thresholds


def test_analyze_element_patch_low_contrast():
    analyzer = VisualContrastAnalyzer()

    # Generate a temporary image with low-contrast patch (light grey on white)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw light grey text-like box
        draw.rectangle([20, 20, 180, 80], fill=(210, 210, 210))
        img.save(tmp_path)

        bbox = BoundingBox(x=10.0, y=10.0, width=180.0, height=80.0)
        issue = analyzer.analyze_element_patch(tmp_path, bbox, is_large_text=False, selector=".subtext")

        assert issue is not None
        assert issue.rule_id == "WCAG_1_4_3_CONTRAST_MINIMUM"
        assert issue.severity in [Severity.CRITICAL, Severity.MAJOR]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_analyze_element_patch_high_contrast_passes():
    analyzer = VisualContrastAnalyzer()

    # Generate image with high-contrast patch (black text block on white background)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Deep black on white
        draw.rectangle([30, 30, 170, 70], fill=(10, 10, 10))
        img.save(tmp_path)

        bbox = BoundingBox(x=10.0, y=10.0, width=180.0, height=80.0)
        # For high contrast, the contrast ratio is ~19:1, so no violation issue should be generated
        issue = analyzer.analyze_element_patch(tmp_path, bbox, is_large_text=False, selector=".hero-title")
        assert issue is None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
