# ─── Stage 1: Builder ─────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# Fix pip SSL issues (corporate proxy / self-signed certs)
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org download.pytorch.org"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1-dev \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU first from the correct index
RUN pip install --no-cache-dir --prefix=/install \
    torch torchaudio torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# Make PyTorch packages visible for the next pip install
ENV PYTHONPATH=/install/lib/python3.13/site-packages

# Install remaining requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Install facenet-pytorch WITHOUT its dependency constraints
RUN pip install --no-cache-dir --prefix=/install --no-deps \
    facenet-pytorch>=2.6.0


# ─── Stage 2: Runtime ────────────────────────────────────
FROM python:3.13-slim

LABEL maintainer="DeepTrace Team"
LABEL description="DeepTrace Flask ML Engine — Deepfake Detection API"

# Non-root user for security
RUN groupadd -r deeptrace && useradd -r -g deeptrace -d /app -s /sbin/nologin deeptrace

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY wsgi.py .
COPY gunicorn.conf.py .

# Create directories and set ownership
RUN mkdir -p logs weights uploads && chown -R deeptrace:deeptrace /app

USER deeptrace

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "wsgi:app", "--config", "gunicorn.conf.py"]
