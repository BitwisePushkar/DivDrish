# ─── Stage 1: Builder ─────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsndfile1-dev libgl1 libglib2.0-0 libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ✅ LAYER 1: PyTorch alone — only re-runs if this RUN line changes
RUN pip install --no-cache-dir --prefix=/install \
    torch==2.5.1+cpu torchaudio==2.5.1+cpu torchvision==0.20.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

ENV PYTHONPATH=/install/lib/python3.13/site-packages

# ✅ LAYER 2: facenet (no deps) — rarely changes
RUN pip install --no-cache-dir --prefix=/install --no-deps \
    "facenet-pytorch>=2.6.0"

# ✅ LAYER 3: requirements — only re-runs when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# ─── Stage 2: Runtime ────────────────────────────────────
FROM python:3.13-slim

RUN groupadd -r deeptrace && useradd -r -g deeptrace -d /app -s /sbin/nologin deeptrace

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 libgl1 libglib2.0-0 libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app
COPY app/ ./app/
COPY wsgi.py gunicorn.conf.py .
RUN mkdir -p logs weights uploads && chown -R deeptrace:deeptrace /app

USER deeptrace
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "wsgi:app", "--config", "gunicorn.conf.py"]