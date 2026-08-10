# =============================================================================
# Hackroot Studio — backend (multi-stage, production)
# =============================================================================
# Stage 1 builds wheels into a venv; Stage 2 is a slim runtime that carries
# only runtime system deps (ffmpeg/libpq/espeak/fonts) + the venv + app code.
# Build tooling (gcc, headers) never reaches the runtime image.

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Build deps needed only to compile wheels (psycopg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install into an isolated venv that we copy to the runtime stage.
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1

# Runtime system deps: ffmpeg (render), libpq (asyncpg driver), curl (healthcheck),
# espeak-ng (mock TTS voice), CJK + emoji fonts for burned-in captions/watermarks.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libpq5 \
        curl \
        espeak-ng \
        fonts-dejavu-core \
        fonts-noto \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user.
RUN groupadd --system app && useradd --system --gid app --home /app app && \
    mkdir -p /app /data/storage && chown -R app:app /app /data/storage

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

USER app
EXPOSE 8000

# tini reaps zombies; uvicorn launched by compose command (alembic + uvicorn).
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
