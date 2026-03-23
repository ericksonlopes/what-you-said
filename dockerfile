# Stage 1: Build the application
FROM python:3.12-slim AS builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv by copying from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /bin/uvx

# Set the working directory
WORKDIR /app

# Copy dependency files using link for faster builds
COPY --link pyproject.toml uv.lock ./

# Install dependencies using cache mount
# Installing all extras to avoid runtime uv sync
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project --locked

# Install Playwright browsers (deps will be installed in runtime)
ENV PLAYWRIGHT_BROWSERS_PATH=/app/data/.ms-playwright
RUN --mount=type=cache,target=/root/.cache/uv \
    mkdir -p /app/data/.ms-playwright && uv run playwright install chromium

# Copy the rest of the application code
# Only do this if needed for a production-like build in this stage
# For dev, we usually volume mount, but for CI/prod we need it.
# Moving this to the end of the builder or skipping if solely using builder for venv.
COPY --link . .

# Final Stage: Runtime
FROM python:3.12-slim AS runtime

# Set the working directory
WORKDIR /app

# Set runtime environment variables
# Note: HF_HOME and TRANSFORMERS_CACHE point to /app/data to persist across container restarts if mounted
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRANSFORMERS_CACHE=/app/data/huggingface_cache \
    HF_HOME=/app/data/huggingface_home \
    PLAYWRIGHT_BROWSERS_PATH=/app/data/.ms-playwright \
    UV_CACHE_DIR=/root/.cache/uv \
    PORT=5000

# Install runtime dependencies
# ffmpeg for transcription, curl for healthchecks
# Explicitly install some common missing libs if install-deps is flaky in slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    plocate \
    libnspr4 libnss3 libnss3-tools libgbm1 libasound2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv for runtime entrypoint
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /bin/uvx

# Create data directory
RUN mkdir -p /app/data/huggingface_cache /app/data/huggingface_home

# Copy ONLY the virtual environment first
# This prevents `uv run` from re-downloading all Python packages just to install Playwright deps.
COPY --from=builder /app/.venv /app/.venv

RUN --mount=type=cache,target=/root/.cache/uv \
    uv run playwright install-deps chromium

# Copy the rest of the application code from the builder
COPY --from=builder /app /app

# Make entrypoint executable
RUN sed -i 's/\r$//' scripts/entrypoint.sh && chmod +x scripts/entrypoint.sh

# Expose FastAPI port
EXPOSE 5000

# Use entrypoint for setup (migrations) and start
# We point to the virtual environment's bin for direct access if needed
ENTRYPOINT ["scripts/entrypoint.sh"]
