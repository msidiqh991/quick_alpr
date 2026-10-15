FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=1 \
    ALPR_APP_TITLE="ALPR Service" \
    ALPR_HOST=0.0.0.0 \
    ALPR_PORT=8001 \
    ALPR_RELOAD=false \
    ALPR_RELOAD_DIR=app \
    ALPR_DOCS_ENABLED=false \
    ALPR_DETECTOR_MODEL=yolo-v9-t-640-license-plate-end2end \
    ALPR_OCR_MODEL=cct-s-v2-global-model \
    ALPR_MAX_UPLOAD_MB=5

WORKDIR /app

RUN groupadd -r appuser \
    && useradd -r -g appuser -d /var/cache/alpr appuser \
    && mkdir -p /var/cache/alpr \
    && chown appuser:appuser /var/cache/alpr

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY README.md ./
RUN uv sync --frozen --no-dev

ENV HOME=/var/cache/alpr \
    XDG_CACHE_HOME=/var/cache/alpr \
    HF_HOME=/var/cache/alpr/huggingface \
    HUGGINGFACE_HUB_CACHE=/var/cache/alpr/huggingface/hub \
    TRANSFORMERS_CACHE=/var/cache/alpr/huggingface/transformers \
    TORCH_HOME=/var/cache/alpr/torch

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=5m --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health/live' % os.environ.get('ALPR_PORT', '8001'), timeout=3).close()"

CMD ["start"]
