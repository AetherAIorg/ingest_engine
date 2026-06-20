from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from ingest.config import MetricGraphSinkConfig

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".sql", ".dax", ".py", ".csv"}


class V1IngestClient:
    """HTTP client for MetricGraph /api/v1 ingest."""

    def __init__(self, config: MetricGraphSinkConfig) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        headers = {}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0, headers=headers)
        self._session_id: str | None = None

    def _context_payload(self) -> dict:
        ctx: dict = {}
        if self.config.owner:
            ctx["owner"] = self.config.owner
        if self.config.team:
            ctx["team"] = self.config.team
        if self.config.domain:
            ctx["domain"] = self.config.domain
        return ctx

    def start_session(self) -> str:
        if self._session_id:
            return self._session_id
        # Create session via empty ingest is wasteful; session created on first upload.
        return ""

    def upload(self, path: str, content: bytes) -> tuple[str | None, str | None]:
        if not self._supported(path):
            logger.info("Skipping unsupported file for MetricGraph: %s", path)
            return None, None
        filename = Path(path).name
        files = {"files": (filename, content)}
        data: dict[str, str] = {}
        ctx = self._context_payload()
        if ctx:
            data["context"] = json.dumps(ctx)
        if self._session_id:
            data["session_id"] = self._session_id
        response = self.client.post("/api/v1/ingest", files=files, data=data)
        response.raise_for_status()
        body = response.json()
        self._session_id = body.get("id")
        artifacts = body.get("artifacts") or []
        artifact_id = artifacts[0]["id"] if artifacts else None
        return artifact_id, self._session_id

    def materialize(self) -> None:
        if not self._session_id:
            return
        response = self.client.post("/api/v1/graph/materialize")
        response.raise_for_status()
        logger.info("Materialized KG for session %s: %s", self._session_id, response.json())

    def reset_session(self) -> None:
        self._session_id = None

    def _supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def close(self) -> None:
        self.client.close()
