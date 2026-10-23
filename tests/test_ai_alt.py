"""Unit tests for AI alternative text generation engine."""

import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch
from PIL import Image
from auditor.vision.ai_alt_generator import AIAltTextGenerator


@pytest.mark.asyncio
async def test_fallback_description_logo():
    generator = AIAltTextGenerator(provider="auto")
    alt = generator._fallback_description(context_hint="", image_path="/static/images/university-logo.png")
    assert "logo" in alt.lower()


@pytest.mark.asyncio
async def test_fallback_description_chart():
    generator = AIAltTextGenerator(provider="auto")
    alt = generator._fallback_description(context_hint="", image_path="/data/charts/quarterly_growth.png")
    assert "chart" in alt.lower()


@pytest.mark.asyncio
async def test_fallback_description_with_hint():
    generator = AIAltTextGenerator(provider="auto")
    alt = generator._fallback_description(context_hint="Student campus library entrance at noon", image_path="")
    assert "student campus library" in alt.lower()


@pytest.mark.asyncio
async def test_generate_alt_text_missing_file_returns_fallback():
    generator = AIAltTextGenerator(provider="auto")
    result = await generator.generate_alt_text("non_existent_image_path.jpg", context_hint="Company Logo")
    assert "logo" in result.lower()


@pytest.mark.asyncio
async def test_mocked_openai_vision_call():
    generator = AIAltTextGenerator(provider="openai")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        img = Image.new("RGB", (50, 50), color=(100, 150, 200))
        img.save(tmp_path)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "choices": [{"message": {"content": "Blue circular brand icon badge"}}]
        }
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with patch("auditor.core.config.settings.OPENAI_API_KEY", "sk-mock-key"):
                alt = await generator._call_openai_vision("base64data", "Brand icon")
                assert alt == "Blue circular brand icon badge"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
