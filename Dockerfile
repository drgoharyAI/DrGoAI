FROM python:3.10-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y tesseract-ocr libsm6 libxext6 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -q -r requirements.txt
COPY . .
RUN mkdir -p logs data/embeddings
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
