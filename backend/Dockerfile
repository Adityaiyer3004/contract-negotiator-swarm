FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt PyPDF2 watchdog requests reportlab python-dotenv

# Copy application source code
COPY backend/ /app/backend/
COPY config/ /app/config/
COPY state/ /app/state/
COPY execution/ /app/execution/
COPY ingestion/ /app/ingestion/
COPY agents/ /app/agents/
COPY .env /app/.env

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
