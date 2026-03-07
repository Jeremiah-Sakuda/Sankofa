FROM python:3.12-slim

# Run as non-root for security
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/false app
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

USER app
EXPOSE 8080

# Production: single worker, no reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
