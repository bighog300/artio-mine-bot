FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install -e ".[dev]"

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
