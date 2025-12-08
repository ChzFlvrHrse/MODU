# Dockerfile
FROM python:3.9-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /backend

# System deps you might need (fonts, tesseract, etc.) – keep minimal for now
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app code
COPY . .

# Expose the internal port
EXPOSE 8000

# Run with Hypercorn (adjust module:app name!)
CMD ["hypercorn", "app:quart_app", "-b", "0.0.0.0:8000", "--workers", "1"]
