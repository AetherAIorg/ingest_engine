from __future__ import annotations

from ingest.store import ContentStore


def test_content_store_put_get_dedup(tmp_path):
    store = ContentStore(tmp_path / "store")
    data = b"same content"
    h1, c1 = store.put(data)
    h2, c2 = store.put(data)
    assert h1 == h2
    assert store.get(h1) == data
    assert c2 == c1  # dedup, same compressed size


def test_content_store_roundtrip(tmp_path):
    store = ContentStore(tmp_path / "store", compression_level=9)
    data = b"x" * 10000
    h, compressed = store.put(data)
    assert compressed < len(data)
    assert store.exists(h)
    assert store.get(h) == data
