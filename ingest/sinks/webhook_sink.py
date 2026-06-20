from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ingest.config import WebhookSinkConfig

logger = logging.getLogger(__name__)


def _event_id(*parts: object) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class WebhookSink:
    """Posts file-change events to the integration hub.

    Emits the canonical hub event schema so the hub's `/webhooks/ingest`
    endpoint can route to Slack/Teams. This sink never returns an artifact id;
    when composed with MetricGraphSink it runs purely for notifications.
    """

    def __init__(self, config: WebhookSinkConfig) -> None:
        self.config = config
        self.url = config.url.rstrip("/") if config.url else ""
        self._client = httpx.Client(timeout=10.0)

    def _emit(self, event: str, path: str, content_hash: str | None, size_bytes: int | None,
              prev_artifact_id: str | None) -> None:
        if not self.url:
            return
        payload = {
            "path": str(Path(path)),
            "content_hash": content_hash,
            "size_bytes": size_bytes,
            "prev_artifact_id": prev_artifact_id,
        }
        body = {
            "source": "ingest",
            "event": event,
            "id": _event_id(event, path, content_hash or prev_artifact_id or ""),
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        headers = {"Content-Type": "application/json"}
        if self.config.secret:
            headers["X-Hub-Secret"] = self.config.secret
        try:
            self._client.post(self.url, json=body, headers=headers)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Webhook sink emit failed for %s: %s", event, exc)

    def on_added(self, path: str, content: bytes, content_hash: str) -> str | None:
        self._emit("file.added", path, content_hash, len(content), None)
        return None

    def on_modified(self, path: str, content: bytes, content_hash: str,
                    prev_artifact_id: str | None) -> str | None:
        self._emit("file.modified", path, content_hash, len(content), prev_artifact_id)
        return None

    def on_removed(self, path: str, prev_artifact_id: str | None) -> None:
        self._emit("file.removed", path, None, None, prev_artifact_id)

    def close(self) -> None:
        self._client.close()
