#!/bin/sh
set -e

cat > /app/config.docker.yaml <<EOF
watch:
  - path: /demo/investment_ops_demo
    recursive: true
    include: ["*.xlsx", "*.sql", "*.dax", "*.py"]
    exclude: ["*.csv"]

poll_interval_seconds: ${INGEST_POLL_INTERVAL:-10}
store_dir: /data/ingest_store
state_db: /data/ingest_state.db
compression_level: 6

sink:
  type: composite
  metricgraph:
    base_url: ${METRICGRAPH_BASE_URL:-http://mg-api:8000}
    api_key: ${INGEST_API_KEY:-}
    delete_on_change: true
    owner: ${INGEST_OWNER:-Investment Operations}
    team: ${INGEST_TEAM:-investment-operations}
    domain: ${INGEST_DOMAIN:-Investment Performance}
  webhook:
    url: ${HUB_WEBHOOK_URL:-http://hub:8080/webhooks/ingest}
    secret: ${HUB_WEBHOOK_SECRET:-change-me}
EOF

exec python -m ingest "$@" -c /app/config.docker.yaml
