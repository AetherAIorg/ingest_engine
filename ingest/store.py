from __future__ import annotations

import zlib
from pathlib import Path

from ingest.hashing import sha256_bytes


class ContentStore:
    """Content-addressed store with zlib compression."""

    def __init__(self, root: Path, compression_level: int = 6) -> None:
        self.root = root
        self.compression_level = compression_level
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, content_hash: str) -> Path:
        return self.root / content_hash[:2] / f"{content_hash}.zz"

    def put(self, data: bytes) -> tuple[str, int]:
        content_hash = sha256_bytes(data)
        dest = self._path_for(content_hash)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            compressed = zlib.compress(data, level=self.compression_level)
            dest.write_bytes(compressed)
            return content_hash, len(compressed)
        return content_hash, dest.stat().st_size

    def get(self, content_hash: str) -> bytes:
        dest = self._path_for(content_hash)
        if not dest.exists():
            raise FileNotFoundError(f"No stored content for hash {content_hash}")
        return zlib.decompress(dest.read_bytes())

    def exists(self, content_hash: str) -> bool:
        return self._path_for(content_hash).exists()
