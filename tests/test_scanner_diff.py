from __future__ import annotations

from ingest.config import WatchEntry
from ingest.diff import ChangeType, compute_diff
from ingest.scanner import FileInfo, scan_paths
from ingest.state import FileRecord, StateStore


def test_scanner_and_diff(tmp_path):
    (tmp_path / "a.sql").write_text("SELECT 1 AS net_irr")
    (tmp_path / "b.py").write_text("def calc_irr(): pass")

    entry = WatchEntry(path=tmp_path, recursive=True, include=["*.sql", "*.py"])
    scanned = scan_paths([entry])
    assert len(scanned) == 2

    changes = compute_diff(scanned, {})
    assert len(changes) == 2
    assert all(c.change_type == ChangeType.ADDED for c in changes)

    # No changes on second scan with known state
    active = {
        s.path: FileRecord(
            path=s.path,
            content_hash=s.content_hash,
            size_bytes=s.size_bytes,
            compressed_size=0,
            mtime=s.mtime,
            status="active",
            artifact_id=None,
            updated_at="",
        )
        for s in scanned
    }
    scanned2 = scan_paths([entry], {p: (r.size_bytes, r.mtime, r.content_hash) for p, r in active.items()})
    assert compute_diff(scanned2, active) == []

    # Modify file
    (tmp_path / "a.sql").write_text("SELECT iterative_irr() AS net_irr")
    scanned3 = scan_paths([entry])
    changes3 = compute_diff(scanned3, active)
    assert len(changes3) == 1
    assert changes3[0].change_type == ChangeType.MODIFIED

    # Remove file
    (tmp_path / "b.py").unlink()
    scanned4 = scan_paths([entry])
    changes4 = compute_diff(scanned4, active)
    removed = [c for c in changes4 if c.change_type == ChangeType.REMOVED]
    assert len(removed) == 1
    assert removed[0].path.endswith("b.py")


def test_state_store(tmp_path):
    db = StateStore(tmp_path / "state.db")
    db.upsert("/a.sql", "hash1", 10, 5, 1.0, artifact_id="art-1")
    rec = db.get("/a.sql")
    assert rec is not None
    assert rec.artifact_id == "art-1"
    db.mark_removed("/a.sql")
    assert db.get("/a.sql").status == "removed"
    db.log_event("/a.sql", "REMOVED")
    assert len(db.list_events()) == 1
    db.close()
