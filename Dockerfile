# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --locked --no-dev --no-install-project

# Copy the rest of the application code
COPY . .

# Install the project itself
RUN uv sync --locked --no-dev

# Expose Streamlit port
EXPOSE 8501

# Command to run migrations and then the application
CMD ["bash", "-c", "uv run alembic upgrade head && uv run streamlit run frontend/streamlit_app.py --server.address=0.0.0.0 --server.port=8501"]
