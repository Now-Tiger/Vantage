# ---------- Stage 1: Build ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Optimized UV configuration
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
# Install dependencies into a standard location for easy copying
ENV UV_PROJECT_ENVIRONMENT="/venv"

WORKDIR /app

# Only copy lockfiles first to maximize layer cache
# If these haven't changed, Docker skips the 'uv sync' step entirely
COPY pyproject.toml uv.lock ./

# Synchronize dependencies
RUN uv sync --frozen --no-dev --no-install-project

# ---------- Stage 2: Runtime ----------
FROM python:3.13-slim AS final

# Standard Python optimizations
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Add the venv to the path so 'uvicorn' and 'python' refer to the venv versions
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

# Copy the pre-built virtual environment
COPY --from=builder /venv /venv

# Copy only the necessary application source code
# Ensure you have a .dockerignore file to exclude __pycache__, .git, and local venvs
COPY . .

# Performance: use the venv's uvicorn directly instead of 'uv run' 
# This removes the need to install 'uv' in the final image, saving space and startup time
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
