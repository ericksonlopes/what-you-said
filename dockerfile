# Stage 1: Build the application
FROM python:3.12-slim AS builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/root/.cache/uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv by copying from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Add build-time argument for GPU support
ARG INSTALL_GPU=false

# Copy only dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies using cache mount
# --no-install-project is used because we haven't copied the source code yet
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$INSTALL_GPU" = "true" ]; then \
        uv sync --frozen --no-dev --no-install-project --extra gpu; \
    else \
        uv sync --frozen --no-dev --no-install-project; \
    fi

# Install Playwright browsers (deps will be installed in runtime)
ENV PLAYWRIGHT_BROWSERS_PATH=/app/data/.ms-playwright
RUN mkdir -p /app/data/.ms-playwright && \
    uv run --no-dev playwright install chromium

# Copy the rest of the application code
COPY . .

# Final Stage: Runtime
FROM python:3.12-slim AS runtime

# Set the working directory
WORKDIR /app

# Set runtime environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/data/huggingface_home \
    PLAYWRIGHT_BROWSERS_PATH=/app/data/.ms-playwright \
    UV_CACHE_DIR=/root/.cache/uv \
    PORT=5000

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    nodejs \
    libnspr4 libnss3 libnss3-tools libgbm1 libasound2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv for runtime entrypoint (useful for dynamic extras)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create data directories
RUN mkdir -p /app/data/huggingface_home /app/data/.ms-playwright

# Copy the virtual environment and application code from the builder
COPY --from=builder /app /app

# Install Playwright dependencies and Crawl4AI setup in the runtime environment
RUN uv run --no-dev playwright install-deps chromium && \
    uv run --no-dev crawl4ai-setup && \
    sed -i 's/\r$//' scripts/entrypoint.sh && \
    chmod +x scripts/entrypoint.sh

# Expose FastAPI port
EXPOSE 5000

# Use entrypoint for setup (migrations) and start
ENTRYPOINT ["scripts/entrypoint.sh"]
