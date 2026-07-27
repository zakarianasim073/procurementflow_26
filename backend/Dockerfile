FROM python:3.12.11-slim-bookworm

ENV PYTHONPATH=/workspace/backend:/workspace \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /workspace/backend

RUN groupadd --system procureflow \
    && useradd --system --gid procureflow --home-dir /workspace/backend procureflow \
    && mkdir -p /data/uploads /data/outputs /data/tenders /data/.procurementflow-system \
        /workspace/backend/runtime \
    && chown -R procureflow:procureflow /data /workspace/backend

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt requirements-cpu.txt ./
RUN python -m pip install --no-cache-dir \
        pip==26.1.2 \
        setuptools==83.0.0 \
    && pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.6.0+cpu \
    && pip install --no-cache-dir -r requirements-cpu.txt \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip \
    && find /usr/local/lib/python3.12/site-packages -type d -name '__pycache__' -prune -exec rm -rf {} +

# Copy app without a duplicate recursive ownership layer. Playwright's browser
# files remain root-owned but world-readable/executable for the runtime user.
COPY --chown=procureflow:procureflow . .

USER procureflow

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
