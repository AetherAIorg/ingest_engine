from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from ingest.config import WatchEntry
from ingest.hashing import hash_file


@dataclass
class FileInfo:
    path: str
    content_hash: str
    size_bytes: int
    mtime: float
    content: bytes


def _matches(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _should_include(path: Path, entry: WatchEntry) -> bool:
    name = path.name
    if entry.exclude and _matches(name, entry.exclude):
        return False
    if entry.include:
        return _matches(name, entry.include)
    return True


def _expand_entry(entry: WatchEntry) -> list[Path]:
    base = entry.path
    if not base.exists():
        return []
    if base.is_file():
        return [base] if _should_include(base, entry) else []
    if not base.is_dir():
        return []
    iterator = base.rglob("*") if entry.recursive else base.glob("*")
    return sorted(p for p in iterator if p.is_file() and _should_include(p, entry))


def scan_paths(
    entries: list[WatchEntry],
    known: dict[str, tuple[int, float, str]] | None = None,
) -> list[FileInfo]:
    """Scan watch entries. known maps path -> (size, mtime, content_hash) for short-circuit."""
    known = known or {}
    results: list[FileInfo] = []
    seen: set[str] = set()

    for entry in entries:
        for path in _expand_entry(entry):
            path_str = str(path.resolve())
            if path_str in seen:
                continue
            seen.add(path_str)
            stat = path.stat()
            size = stat.st_size
            mtime = stat.st_mtime
            prev = known.get(path_str)
            if prev and prev[0] == size and prev[1] == mtime:
                content_hash, content = prev[2], b""
            else:
                content_hash, content = hash_file(path)
            results.append(
                FileInfo(
                    path=path_str,
                    content_hash=content_hash,
                    size_bytes=size,
                    mtime=mtime,
                    content=content,
                )
            )
    return results
