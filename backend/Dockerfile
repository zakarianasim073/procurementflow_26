FROM python:3.12.11-slim-bookworm

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt requirements-cpu.txt ./
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.6.0+cpu \
    && pip install --no-cache-dir -r requirements-cpu.txt \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip \
    && find /usr/local/lib/python3.12/site-packages -type d -name '__pycache__' -prune -exec rm -rf {} +

# Copy app
COPY . .
RUN mkdir -p /app/backend \
    && cp -a /app/crawler /app/backend/crawler \
    && touch /app/backend/__init__.py

# Create runtime directories
RUN mkdir -p /data/uploads /data/outputs /data/tenders /data/.procurementflow-system
RUN groupadd --system procureflow \
    && useradd --system --gid procureflow --home-dir /app procureflow \
    && chown -R procureflow:procureflow /app /data

USER procureflow

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
