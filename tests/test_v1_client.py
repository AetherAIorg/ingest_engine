from __future__ import annotations

from ingest.config import MetricGraphSinkConfig
from ingest.sinks.v1_client import V1IngestClient


def test_v1_client_context_payload():
    cfg = MetricGraphSinkConfig(
        api_key="mg_test_x",
        owner="Ops",
        team="investment-ops",
        domain="Performance",
    )
    client = V1IngestClient(cfg)
    assert client._context_payload() == {
        "owner": "Ops",
        "team": "investment-ops",
        "domain": "Performance",
    }
    client.close()
