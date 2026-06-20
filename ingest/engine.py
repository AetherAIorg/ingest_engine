from __future__ import annotations

import logging
import signal
import time
from pathlib import Path

from ingest.config import IngestConfig
from ingest.diff import ChangeType, FileChange, compute_diff
from ingest.scanner import scan_paths
from ingest.sinks.composite_sink import CompositeSink
from ingest.sinks.log_sink import LogSink
from ingest.sinks.metricgraph_sink import MetricGraphSink
from ingest.sinks.webhook_sink import WebhookSink
from ingest.state import StateStore
from ingest.store import ContentStore

logger = logging.getLogger(__name__)


class IngestEngine:
    def __init__(self, config: IngestConfig) -> None:
        self.config = config
        self.store = ContentStore(config.store_dir, config.compression_level)
        self.state = StateStore(config.state_db)
        self.sink = self._build_sink()
        self._running = True

    def _build_sink(self):
        sink_type = self.config.sink.type
        if sink_type == "metricgraph":
            return MetricGraphSink(self.config.sink.metricgraph)
        if sink_type == "webhook":
            return WebhookSink(self.config.sink.webhook)
        if sink_type == "composite":
            # MetricGraph is the primary (its artifact id is canonical); the
            # webhook sink runs alongside it purely for notifications.
            return CompositeSink(
                primary=MetricGraphSink(self.config.sink.metricgraph),
                secondaries=[WebhookSink(self.config.sink.webhook)],
            )
        return LogSink()

    def stop(self) -> None:
        self._running = False

    def _known_for_scan(self) -> dict[str, tuple[int, float, str]]:
        active = self.state.get_active_files()
        return {
            path: (rec.size_bytes, rec.mtime, rec.content_hash)
            for path, rec in active.items()
        }

    def _read_content(self, change: FileChange) -> bytes:
        if change.file_info and change.file_info.content:
            return change.file_info.content
        return Path(change.path).read_bytes()

    def _process_change(self, change: FileChange) -> None:
        path = change.path
        if change.change_type == ChangeType.REMOVED:
            prev_id = change.previous.artifact_id if change.previous else None
            self.sink.on_removed(path, prev_id)
            self.state.mark_removed(path)
            self.state.log_event(path, ChangeType.REMOVED.value, detail=f"artifact={prev_id}")
            logger.info("Processed REMOVED %s", path)
            return

        assert change.file_info is not None
        content = self._read_content(change)
        content_hash, compressed_size = self.store.put(content)
        artifact_id: str | None = None

        if change.change_type == ChangeType.ADDED:
            artifact_id = self.sink.on_added(path, content, content_hash)
            self.state.log_event(path, ChangeType.ADDED.value, content_hash)
        elif change.change_type == ChangeType.MODIFIED:
            prev_id = change.previous.artifact_id if change.previous else None
            artifact_id = self.sink.on_modified(path, content, content_hash, prev_id)
            self.state.log_event(
                path,
                ChangeType.MODIFIED.value,
                content_hash,
                detail=f"prev_hash={change.previous.content_hash if change.previous else None}",
            )

        self.state.upsert(
            path=path,
            content_hash=content_hash,
            size_bytes=len(content),
            compressed_size=compressed_size,
            mtime=change.file_info.mtime,
            artifact_id=artifact_id,
        )
        logger.info("Processed %s %s", change.change_type.value, path)

    def scan_once(self) -> int:
        active = self.state.get_active_files()
        scanned = scan_paths(self.config.watch, self._known_for_scan())
        changes = compute_diff(scanned, active)
        for change in changes:
            try:
                self._process_change(change)
            except Exception:
                logger.exception("Failed to process change for %s", change.path)
        if hasattr(self.sink, "end_scan_cycle"):
            self.sink.end_scan_cycle()
        return len(changes)

    def run(self) -> None:
        def _handle_signal(_signum, _frame):
            logger.info("Shutdown requested")
            self.stop()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        logger.info(
            "Ingest engine started (interval=%ss, sink=%s)",
            self.config.poll_interval_seconds,
            self.config.sink.type,
        )
        while self._running:
            count = self.scan_once()
            if count:
                logger.info("Scan complete: %d change(s)", count)
            time.sleep(self.config.poll_interval_seconds)

    def close(self) -> None:
        if hasattr(self.sink, "close"):
            self.sink.close()
        self.state.close()
