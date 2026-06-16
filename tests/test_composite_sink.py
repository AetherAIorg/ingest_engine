from __future__ import annotations

from dataclasses import dataclass, field

from ingest.sinks.composite_sink import CompositeSink


@dataclass
class RecordingSink:
    name: str = "sink"
    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    return_id: str | None = None
    closed: bool = False

    def on_added(self, path, content, content_hash):
        self.added.append(path)
        return self.return_id

    def on_modified(self, path, content, content_hash, prev_artifact_id):
        self.modified.append(path)
        return self.return_id

    def on_removed(self, path, prev_artifact_id):
        self.removed.append(path)

    def close(self):
        self.closed = True


class BoomSink(RecordingSink):
    def on_added(self, path, content, content_hash):
        raise RuntimeError("boom")


def test_composite_returns_primary_artifact_id_and_fans_out():
    primary = RecordingSink(name="primary", return_id="artifact-1")
    secondary = RecordingSink(name="secondary")
    composite = CompositeSink(primary, [secondary])

    artifact_id = composite.on_added("/x.sql", b"data", "hash")
    assert artifact_id == "artifact-1"
    assert primary.added == ["/x.sql"]
    assert secondary.added == ["/x.sql"]


def test_composite_isolates_secondary_failures():
    primary = RecordingSink(name="primary", return_id="artifact-1")
    composite = CompositeSink(primary, [BoomSink(name="bad")])
    # Secondary raising must not prevent the primary id from being returned.
    assert composite.on_added("/x.sql", b"data", "hash") == "artifact-1"


def test_composite_close_closes_all():
    primary = RecordingSink(name="primary")
    secondary = RecordingSink(name="secondary")
    composite = CompositeSink(primary, [secondary])
    composite.close()
    assert primary.closed and secondary.closed
