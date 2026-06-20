from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ingest.scanner import FileInfo
from ingest.state import FileRecord


class ChangeType(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"


@dataclass
class FileChange:
    change_type: ChangeType
    path: str
    file_info: FileInfo | None = None
    previous: FileRecord | None = None


def compute_diff(
    scanned: list[FileInfo],
    active_state: dict[str, FileRecord],
) -> list[FileChange]:
    changes: list[FileChange] = []
    scanned_by_path = {f.path: f for f in scanned}

    for path, info in scanned_by_path.items():
        prev = active_state.get(path)
        if prev is None:
            changes.append(FileChange(ChangeType.ADDED, path, file_info=info))
        elif prev.content_hash != info.content_hash:
            changes.append(FileChange(ChangeType.MODIFIED, path, file_info=info, previous=prev))

    for path, prev in active_state.items():
        if path not in scanned_by_path:
            changes.append(FileChange(ChangeType.REMOVED, path, previous=prev))

    return changes
