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
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY README.md ./
RUN uv sync --frozen --no-dev

RUN python -c "from app import config; from fast_alpr import ALPR; ALPR(detector_model=config.DETECTOR_MODEL, ocr_model=config.OCR_MODEL, ocr_device='cpu')"
RUN chown -R appuser:appuser /app /opt/venv

USER appuser

EXPOSE 8001
CMD ["start"]
