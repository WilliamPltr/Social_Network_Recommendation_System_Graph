FROM python:3.11-slim

WORKDIR /tests

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Ensure the copied `app` package is importable as a top-level module.
ENV PYTHONPATH=/tests

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tests/requirements.txt
RUN pip install --no-cache-dir -r /tests/requirements.txt

# Copy app and tests so imports are consistent with the API container.
COPY app /tests/app
COPY tests /tests/tests

CMD ["pytest", "-q"]


