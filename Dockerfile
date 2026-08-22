FROM python:3.12-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8050
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8050"]
