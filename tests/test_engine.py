from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ingest.config import IngestConfig, SinkConfig, WatchEntry
from ingest.engine import IngestEngine


@dataclass
class FakeSink:
    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    artifact_counter: int = 0

    def on_added(self, path: str, content: bytes, content_hash: str) -> str | None:
        self.added.append(path)
        self.artifact_counter += 1
        return f"artifact-{self.artifact_counter}"

    def on_modified(self, path: str, content: bytes, content_hash: str, prev_artifact_id: str | None) -> str | None:
        self.modified.append(path)
        self.artifact_counter += 1
        return f"artifact-{self.artifact_counter}"

    def on_removed(self, path: str, prev_artifact_id: str | None) -> None:
        self.removed.append(path)


def test_engine_detects_add_and_modify(tmp_path):
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    sql_file = watch_dir / "deal.sql"
    sql_file.write_text("SELECT 1 AS irr")

    config = IngestConfig(
        watch=[WatchEntry(path=watch_dir, include=["*.sql"])],
        poll_interval_seconds=1,
        store_dir=tmp_path / "store",
        state_db=tmp_path / "state.db",
        sink=SinkConfig(type="log"),
    )
    engine = IngestEngine(config)
    fake = FakeSink()
    engine.sink = fake

    assert engine.scan_once() == 1
    assert len(fake.added) == 1

    sql_file.write_text("SELECT iterative_irr() AS irr")
    assert engine.scan_once() == 1
    assert len(fake.modified) == 1

    rec = engine.state.get(str(sql_file.resolve()))
    assert rec is not None
    assert rec.artifact_id == "artifact-2"

    engine.close()
