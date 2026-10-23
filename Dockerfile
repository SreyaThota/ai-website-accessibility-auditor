# ==============================================================================
# Multi-Stage Dockerfile: AI Website Accessibility Auditor
# Stages:
#   1. base-builder: Compiles dependencies and wheels
#   2. backend: FastAPI REST service with Playwright Chromium driver
#   3. frontend: Streamlit Interactive Executive Dashboard
# ==============================================================================

FROM python:3.12-slim AS base-builder

WORKDIR /build

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ==============================================================================
# Backend Runner Stage (FastAPI + Playwright Chromium)
# ==============================================================================
FROM python:3.12-slim AS backend

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/root/.local/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HEADLESS_BROWSER=true \
    PORT=8000

# Install system dependencies required by Playwright Headless Chromium and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    libjpeg62-turbo \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed wheels from builder
COPY --from=base-builder /root/.local /root/.local

# Install Playwright Chromium headless driver
RUN playwright install chromium

# Copy application source code
COPY auditor /app/auditor
COPY backend /app/backend
COPY data /app/data
COPY pytest.ini /app/pytest.ini

# Create reports and screenshots directory
RUN mkdir -p /app/reports/screenshots

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==============================================================================
# Frontend Runner Stage (Streamlit UI)
# ==============================================================================
FROM python:3.12-slim AS frontend

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/root/.local/bin:$PATH \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    API_URL=http://backend:8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=base-builder /root/.local /root/.local

COPY auditor /app/auditor
COPY frontend /app/frontend
COPY data /app/data

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "frontend/app.py"]
