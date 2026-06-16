from __future__ import annotations

import logging

from ingest.sinks.base import Sink

logger = logging.getLogger(__name__)


class CompositeSink:
    """Fan-out sink that forwards every change to a list of child sinks.

    The first child is treated as the "primary": its returned artifact id is
    the canonical id persisted in state and passed to other sinks on later
    modify/remove events. Secondary sinks (e.g. notifications) run for their
    side effects and a per-sink failure never blocks the others.
    """

    def __init__(self, primary: Sink, secondaries: list[Sink]) -> None:
        self.primary = primary
        self.secondaries = secondaries

    def _run_secondaries(self, method: str, *args) -> None:
        for sink in self.secondaries:
            try:
                getattr(sink, method)(*args)
            except Exception:
                logger.exception("Secondary sink %s failed on %s", type(sink).__name__, method)

    def on_added(self, path: str, content: bytes, content_hash: str) -> str | None:
        artifact_id = self.primary.on_added(path, content, content_hash)
        self._run_secondaries("on_added", path, content, content_hash)
        return artifact_id

    def on_modified(self, path: str, content: bytes, content_hash: str,
                    prev_artifact_id: str | None) -> str | None:
        artifact_id = self.primary.on_modified(path, content, content_hash, prev_artifact_id)
        self._run_secondaries("on_modified", path, content, content_hash, prev_artifact_id)
        return artifact_id

    def on_removed(self, path: str, prev_artifact_id: str | None) -> None:
        self.primary.on_removed(path, prev_artifact_id)
        self._run_secondaries("on_removed", path, prev_artifact_id)

    def close(self) -> None:
        for sink in [self.primary, *self.secondaries]:
            if hasattr(sink, "close"):
                try:
                    sink.close()
                except Exception:
                    logger.exception("Failed to close sink %s", type(sink).__name__)
