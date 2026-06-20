from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LogSink:
    def on_added(self, path: str, content: bytes, content_hash: str) -> str | None:
        logger.info("ADDED %s hash=%s size=%d", path, content_hash[:12], len(content))
        return None

    def on_modified(
        self,
        path: str,
        content: bytes,
        content_hash: str,
        prev_artifact_id: str | None,
    ) -> str | None:
        logger.info(
            "MODIFIED %s hash=%s size=%d prev_artifact=%s",
            path,
            content_hash[:12],
            len(content),
            prev_artifact_id,
        )
        return None

    def on_removed(self, path: str, prev_artifact_id: str | None) -> None:
        logger.info("REMOVED %s prev_artifact=%s", path, prev_artifact_id)
