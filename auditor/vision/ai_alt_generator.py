import os
import base64
from pathlib import Path
from typing import Optional
from PIL import Image
import httpx
from auditor.core.config import settings
from auditor.core.logging import logger

class AIAltTextGenerator:
    """
    Automated Multi-Modal Vision Engine for Accessible Alternative Text Generation.
    Supports OpenAI (gpt-4o), Anthropic (claude-3-5-sonnet), local Ollama (llava),
    and a zero-cloud fallback heuristic vision descriptor.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or settings.VISION_PROVIDER).lower()

    async def generate_alt_text(
        self,
        image_path: str,
        context_hint: str = "",
        crop_box: Optional[tuple] = None,
    ) -> str:
        """
        Generates a concise, context-aware alt text description for an image.
        Target length: 1 to 2 factual sentences, max 125 characters.
        """
        if not os.path.exists(image_path):
            return self._fallback_description(context_hint)

        # Prepare base64 representation
        base64_img = self._encode_image(image_path, crop_box)
        if not base64_img:
            return self._fallback_description(context_hint)

        # Try configured multi-modal provider
        if self.provider in ["openai", "auto"] and settings.OPENAI_API_KEY:
            try:
                return await self._call_openai_vision(base64_img, context_hint)
            except Exception as e:
                logger.warning(f"OpenAI vision generation failed: {e}. Falling back.")

        if self.provider in ["anthropic", "auto"] and settings.ANTHROPIC_API_KEY:
            try:
                return await self._call_anthropic_vision(base64_img, context_hint)
            except Exception as e:
                logger.warning(f"Anthropic vision generation failed: {e}. Falling back.")

        if self.provider in ["ollama", "auto"]:
            try:
                return await self._call_ollama_vision(base64_img, context_hint)
            except Exception:
                pass  # Ollama not running or unavailable

        # Fallback local heuristic synthesizer
        return self._fallback_description(context_hint, image_path)

    async def _call_openai_vision(self, base64_img: str, hint: str) -> str:
        """Calls OpenAI gpt-4o vision completions API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        prompt = (
            "Provide a concise, factual, WCAG-compliant alt text description for this web element. "
            "Do not start with 'image of' or 'picture of'. Maximum 15 words. "
            f"Context: {hint}"
        )
        payload = {
            "model": settings.OPENAI_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}},
                    ],
                }
            ],
            "max_tokens": 60,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip().strip('"')

    async def _call_anthropic_vision(self, base64_img: str, hint: str) -> str:
        """Calls Anthropic Claude 3.5 Sonnet vision API."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        prompt = (
            "Write a concise, objective WCAG-compliant alt text description for this image. "
            "Under 15 words. Do not use 'image of'. "
            f"Surrounding context: {hint}"
        )
        payload = {
            "model": settings.ANTHROPIC_VISION_MODEL,
            "max_tokens": 60,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/png", "data": base64_img},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
            return data["content"][0]["text"].strip().strip('"')

    async def _call_ollama_vision(self, base64_img: str, hint: str) -> str:
        """Calls local Ollama multi-modal vision service (llava)."""
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        payload = {
            "model": settings.OLLAMA_VISION_MODEL,
            "prompt": f"Write a concise, factual alt text description for this web element in under 15 words. Context: {hint}",
            "images": [base64_img],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            return res.json().get("response", "").strip().strip('"')

    def _encode_image(self, image_path: str, crop_box: Optional[tuple] = None) -> Optional[str]:
        """Loads and converts image or crop to base64 string."""
        import io
        try:
            with Image.open(image_path) as img:
                if crop_box:
                    x1, y1, x2, y2 = crop_box
                    if x2 > x1 and y2 > y1:
                        img = img.crop(crop_box)
                # Resize if excessively large to preserve bandwidth/memory
                img.thumbnail((800, 800))
                buffered = io.BytesIO()
                img.convert("RGB").save(buffered, format="JPEG", quality=85)
                return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            logger.warning(f"Error encoding image for vision AI: {e}")
            return None

    def _fallback_description(self, context_hint: str = "", image_path: str = "") -> str:
        """Deterministic context-aware heuristic fallback for offline environments."""
        clean_hint = context_hint.strip()
        filename = Path(image_path).name.lower() if image_path else ""
        full_path = (image_path or "").lower()

        if "logo" in filename or "logo" in clean_hint.lower() or "logo" in full_path:
            return "Institutional organization logo"
        if "avatar" in filename or "user" in filename or "avatar" in full_path:
            return "User account profile icon"
        if "icon" in filename or "icon" in full_path:
            return "Navigation utility icon"
        if "chart" in filename or "graph" in filename or "chart" in full_path or "graph" in full_path:
            return "Data distribution chart displaying metrics"
        if clean_hint:
            # Capitalize and limit
            words = clean_hint.split()[:8]
            return " ".join(words).capitalize()

        return "Informational graphic illustration"


# Singleton instance
ai_alt_generator = AIAltTextGenerator()
