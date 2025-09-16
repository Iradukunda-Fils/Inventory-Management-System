# ============================================
# Dockerfile for Django + Gunicorn + Nginx
# Multi-stage build
# ============================================

ARG IMAGE_VERSION=3.13.7-slim-bookworm

# ----------------------------
# BUILD STAGE
# ----------------------------
FROM python:${IMAGE_VERSION} AS build

LABEL org.opencontainers.image.authors="iradukundafils1@gmail.com" \
    org.opencontainers.image.title="Inventory_MS" \
    org.opencontainers.image.description="Django + Gunicorn + Nginx multi-stage image" \
    org.opencontainers.image.version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install minimal system deps and uv (astral)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        gcc \
        libpq-dev \
        python3-dev \
        ca-certificates && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/*


# Copy dependency descriptors first (better cache)
COPY pyproject.toml uv.lock ./

# Install Python deps in virtualenv at /app/.venv
RUN uv sync

# Copy project source
COPY --chown=root:root . .

# Collect static files & cleanup cache/pyc
RUN uv run manage.py collectstatic --noinput && \
    find /app -type d -name "__pycache__" -exec rm -r {} + && \
    find /app -name "*.py[co]" -delete && \
    chmod -R 755 /app/.venv


# ----------------------------
# RUNTIME STAGE
# ----------------------------
FROM python:${IMAGE_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive 

WORKDIR /app

# Create non-root user before copying files
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home --shell /sbin/nologin appuser

# Copy built app + venv from build stage
COPY --chown=appuser:appgroup --from=build /app /app

# Add the virtualenv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Install only runtime deps
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        nginx \
        netcat-openbsd supervisor && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/nginx/sites-enabled/default && \
    mkdir -p /run/nginx && \
    if [ -f /app/nginx/nginx.conf ]; then mv /app/nginx/nginx.conf /etc/nginx/conf.d/default.conf; fi && \
    # Create necessary directories and set permissions
    mkdir -p /var/lib/nginx/body /var/lib/nginx/tmp /var/log/nginx \
    && chown -R appuser:appgroup /var/lib/nginx /var/log/nginx /run/nginx \
    && mkdir -p /var/log/supervisor && \ 
    mv ./supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80 8000

USER root   

# Start Nginx and Gunicorn
CMD ["/bin/sh", "-c", "nginx && /app/.venv/bin/gunicorn Inventory_MS.wsgi:application --bind 0.0.0.0:8000 --workers 4"]

# Run the application with supervisord
# CMD ["/usr/bin/supervisord", "-n"]

