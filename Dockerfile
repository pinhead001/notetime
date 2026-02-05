# Use Python 3.12 as base image (matching .python-version)
FROM python:3.12-slim

# Build arguments for version info
ARG GIT_BRANCH=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

# Labels for image metadata
LABEL org.opencontainers.image.source="https://github.com/pinhead001/notetime"
LABEL org.opencontainers.image.description="Notetime - Weekly task and time-tracking app"
LABEL git.branch="${GIT_BRANCH}"
LABEL git.commit="${GIT_COMMIT}"
LABEL build.date="${BUILD_DATE}"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY notetime/ ./notetime/
COPY templates/ ./templates/
COPY static/ ./static/
COPY rules.md .

# Create directory for SQLite database (if needed for local development)
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///./data/notetime.db
ENV GIT_BRANCH=${GIT_BRANCH}
ENV GIT_COMMIT=${GIT_COMMIT}
ENV BUILD_DATE=${BUILD_DATE}

# Run the application
CMD ["uvicorn", "notetime.main:app", "--host", "0.0.0.0", "--port", "8000"]
