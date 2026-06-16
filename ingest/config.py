from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WatchEntry:
    path: Path
    recursive: bool = True
    include: list[str] = field(default_factory=lambda: ["*"])
    exclude: list[str] = field(default_factory=list)


@dataclass
class MetricGraphSinkConfig:
    base_url: str = "http://localhost:8000"
    delete_on_change: bool = True
    owner: str | None = None


@dataclass
class SinkConfig:
    type: str = "log"
    metricgraph: MetricGraphSinkConfig = field(default_factory=MetricGraphSinkConfig)


@dataclass
class IngestConfig:
    watch: list[WatchEntry]
    poll_interval_seconds: int = 5
    store_dir: Path = Path("./.ingest_store")
    state_db: Path = Path("./.ingest_state.db")
    compression_level: int = 6
    sink: SinkConfig = field(default_factory=SinkConfig)


def _parse_watch_entry(raw: dict[str, Any], base_dir: Path) -> WatchEntry:
    path = Path(raw["path"])
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return WatchEntry(
        path=path,
        recursive=bool(raw.get("recursive", True)),
        include=list(raw.get("include", ["*"])),
        exclude=list(raw.get("exclude", [])),
    )


def load_config(path: str | Path) -> IngestConfig:
    config_path = Path(path).resolve()
    base_dir = config_path.parent
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    watch_raw = raw.get("watch") or []
    if not watch_raw:
        raise ValueError("config must define at least one watch entry")

    watch = [_parse_watch_entry(entry, base_dir) for entry in watch_raw]

    sink_raw = raw.get("sink") or {}
    mg_raw = sink_raw.get("metricgraph") or {}
    sink = SinkConfig(
        type=str(sink_raw.get("type", "log")),
        metricgraph=MetricGraphSinkConfig(
            base_url=str(mg_raw.get("base_url", "http://localhost:8000")),
            delete_on_change=bool(mg_raw.get("delete_on_change", True)),
            owner=mg_raw.get("owner"),
        ),
    )

    return IngestConfig(
        watch=watch,
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 5)),
        store_dir=(base_dir / raw.get("store_dir", "./.ingest_store")).resolve(),
        state_db=(base_dir / raw.get("state_db", "./.ingest_state.db")).resolve(),
        compression_level=int(raw.get("compression_level", 6)),
        sink=sink,
    )
