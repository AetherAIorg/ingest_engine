from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ingest.config import MetricGraphSinkConfig

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".sql", ".dax", ".py", ".csv"}


class MetricGraphSink:
    def __init__(self, config: MetricGraphSinkConfig) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0)

    def _supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _upload(self, path: str, content: bytes) -> str | None:
        if not self._supported(path):
            logger.info("Skipping unsupported file for MetricGraph: %s", path)
            return None
        filename = Path(path).name
        files = {"files": (filename, content)}
        response = self.client.post("/api/artifacts/upload", files=files)
        response.raise_for_status()
        data = response.json()
        artifacts = data.get("artifacts") or []
        if not artifacts:
            return None
        return artifacts[0]["id"]

    def _delete(self, artifact_id: str | None) -> None:
        if not artifact_id:
            return
        response = self.client.delete(f"/api/artifacts/{artifact_id}")
        if response.status_code == 404:
            logger.warning("Artifact %s not found during delete", artifact_id)
            return
        response.raise_for_status()

    def on_added(self, path: str, content: bytes, content_hash: str) -> str | None:
        artifact_id = self._upload(path, content)
        logger.info("Uploaded %s -> artifact %s", path, artifact_id)
        return artifact_id

    def on_modified(
        self,
        path: str,
        content: bytes,
        content_hash: str,
        prev_artifact_id: str | None,
    ) -> str | None:
        if self.config.delete_on_change and prev_artifact_id:
            self._delete(prev_artifact_id)
        artifact_id = self._upload(path, content)
        logger.info("Re-uploaded %s -> artifact %s (was %s)", path, artifact_id, prev_artifact_id)
        return artifact_id

    def on_removed(self, path: str, prev_artifact_id: str | None) -> None:
        if self.config.delete_on_change:
            self._delete(prev_artifact_id)
        logger.info("Removed %s from MetricGraph (artifact %s)", path, prev_artifact_id)

    def close(self) -> None:
        self.client.close()
