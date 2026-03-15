# Use an official Python runtime as a parent image
FROM mcr.microsoft.com/vscode/devcontainers/python:3.12

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    ffmpeg \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

# Set the working directory
WORKDIR /workspace

# Copy the dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Pre-install dependencies (without the current package)
RUN uv sync --locked --no-dev --no-install-project

# Default shell
ENV SHELL /bin/bash

# Expose Streamlit port
EXPOSE 8501
