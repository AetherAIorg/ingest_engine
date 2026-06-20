FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingest ./ingest
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

ENV PYTHONPATH=/app
ENV INGEST_CONFIG=/app/config.docker.yaml

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["run"]
