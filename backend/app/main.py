from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from auditor.core.config import settings
from auditor.core.logging import logger
from backend.app.api.routes import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan lifecycle context manager."""
    logger.info("=" * 60)
    logger.info("Starting AI Website Accessibility Auditor API")
    logger.info("Compliance: WCAG 2.1 Level AA & European Accessibility Act (EAA)")
    logger.info(f"Vision Provider: {settings.VISION_PROVIDER}")
    logger.info(f"Reports Directory: {settings.REPORTS_DIR}")
    logger.info("=" * 60)
    yield
    logger.info("Shutting down AI Website Accessibility Auditor API.")

app = FastAPI(
    title="AI Website Accessibility Auditor API",
    version="1.0.0",
    description=(
        "Enterprise-grade WCAG 2.1 AA & European Accessibility Act (EAA) compliance engine. "
        "Performs headless browser DOM crawling, multi-modal pixel contrast analysis, "
        "touch target size verification, and automated AI alt-text generation."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for Streamlit / external dashboard clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api/v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
