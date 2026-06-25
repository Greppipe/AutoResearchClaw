FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    default-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
RUN python -m spacy download en_core_web_sm

COPY . .

CMD ["celery", "-A", "celery_app", "worker", "-Q", "pipeline", "-c", "2", "--loglevel=info", "--without-gossip", "--without-mingle"]
