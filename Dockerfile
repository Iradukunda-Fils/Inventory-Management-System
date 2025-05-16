# Use slim version of Python image (significantly smaller)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive 

# Set working directory
WORKDIR /app

# Pre-install dependencies to speed up layer caching
COPY requirements.txt .

# Install system packages needed for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    netcat-openbsd \
    libffi-dev \
    libssl-dev \
    build-essential \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create system group and user
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home --shell /sbin/nologin appuser


# Copy files with ownership (requires BuildKit)
COPY --chown=appuser:appgroup ./ ./

# Set permissions if needed
RUN chmod -R 755 /app

# Expose Django's port
EXPOSE 8000

# Switch to non-root user
USER appuser


# Entrypoint and default command
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["gunicorn", "Inventory_MS.wsgi:application", "--bind", "0.0.0.0:8000"]