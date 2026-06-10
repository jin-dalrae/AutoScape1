# Dockerfile for RAG Enhancement API
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

# Copy all Python files
COPY *.py ./

# Port
EXPOSE 8080

# Run the API (Cloud Run sets PORT env var automatically; use exec form for proper signal handling)
CMD ["uvicorn", "rag_enhancement_api:app", "--host", "0.0.0.0", "--port", "8080"]
