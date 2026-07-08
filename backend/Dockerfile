FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EMBEDDING_MODEL=all-MiniLM-L6-v2

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

ARG PRELOAD_EMBEDDING_MODEL=false
RUN if [ "$PRELOAD_EMBEDDING_MODEL" = "true" ]; then \
      python scripts/download_embedding_model.py --model "$EMBEDDING_MODEL"; \
    fi

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
