from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> tuple[str, bytes]:
    content = path.read_bytes()
    return sha256_bytes(content), content
