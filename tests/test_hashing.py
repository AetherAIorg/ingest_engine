from __future__ import annotations

from ingest.hashing import hash_file, sha256_bytes


def test_sha256_bytes():
    assert sha256_bytes(b"hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_hash_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("metric data")
    h, content = hash_file(f)
    assert len(h) == 64
    assert content == b"metric data"
