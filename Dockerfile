FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt

# Install the Chromium build that matches the Playwright version installed
# through Crawl4AI, along with its Linux system dependencies.
RUN python -m playwright install --with-deps chromium
RUN python -m patchright install chromium

COPY . .

ENV PYTHONPATH=/app
ENV CRAWL_DIR=/app/job_crawler

CMD ["uvicorn", "job_crawler.api:app", "--host", "0.0.0.0", "--port", "8000"]
