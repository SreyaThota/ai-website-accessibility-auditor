import os
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """Configuration settings for AI Website Accessibility Auditor."""
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Browser & Crawler settings
    HEADLESS_BROWSER: bool = True
    VIEWPORT_WIDTH: int = 1280
    VIEWPORT_HEIGHT: int = 800
    CRAWL_TIMEOUT_MS: int = 30000

    # Storage paths
    REPORTS_DIR: str = str(PROJECT_ROOT / "reports")
    SCREENSHOTS_DIR: str = str(PROJECT_ROOT / "reports" / "screenshots")
    DEMO_SITES_DIR: str = str(PROJECT_ROOT / "data" / "demo_sites")

    # Multi-Modal Vision AI settings
    VISION_PROVIDER: Literal["auto", "local", "openai", "anthropic", "ollama"] = "auto"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_VISION_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_VISION_MODEL: str = "claude-3-5-sonnet-20240620"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_VISION_MODEL: str = "llava:7b"

    # Contrast evaluation parameters (WCAG 2.1 AA)
    MIN_NORMAL_CONTRAST: float = 4.5
    MIN_LARGE_CONTRAST: float = 3.0
    MIN_TOUCH_TARGET_SIZE: int = 44  # CSS px (WCAG 2.5.5)
    MIN_TOUCH_TARGET_AA: int = 24    # CSS px (WCAG 2.5.8)

settings = Settings()

# Ensure reports directories exist
Path(settings.REPORTS_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)
