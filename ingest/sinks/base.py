from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Sink(Protocol):
    def on_added(self, path: str, content: bytes, content_hash: str) -> str | None: ...

    def on_modified(
        self,
        path: str,
        content: bytes,
        content_hash: str,
        prev_artifact_id: str | None,
    ) -> str | None: ...

    def on_removed(self, path: str, prev_artifact_id: str | None) -> None: ...
