from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ingest.config import load_config
from ingest.engine import IngestEngine
from ingest.state import StateStore


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_run(config_path: Path, verbose: bool) -> int:
    config = load_config(config_path)
    engine = IngestEngine(config)
    try:
        engine.run()
    finally:
        engine.close()
    return 0


def cmd_scan_once(config_path: Path, verbose: bool) -> int:
    config = load_config(config_path)
    engine = IngestEngine(config)
    try:
        count = engine.scan_once()
        print(f"Processed {count} change(s)")
    finally:
        engine.close()
    return 0


def cmd_status(config_path: Path) -> int:
    config = load_config(config_path)
    state = StateStore(config.state_db)
    try:
        files = state.list_files()
        if not files:
            print("No tracked files.")
            return 0
        print(f"{'PATH':<50} {'STATUS':<8} {'HASH':<14} {'RATIO':<8} ARTIFACT")
        print("-" * 100)
        for rec in files:
            ratio = (
                f"{rec.compressed_size / rec.size_bytes:.0%}"
                if rec.size_bytes > 0
                else "n/a"
            )
            print(
                f"{rec.path:<50} {rec.status:<8} {rec.content_hash[:12]:<14} {ratio:<8} {rec.artifact_id or '-'}"
            )
        events = state.list_events(10)
        if events:
            print("\nRecent events:")
            for ev in events:
                print(f"  [{ev['created_at']}] {ev['event_type']} {ev['path']}")
    finally:
        state.close()
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="File ingestion engine")
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--verbose", "-v", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="Run continuous polling loop")
    sub.add_parser("scan-once", help="Run a single scan pass")
    sub.add_parser("status", help="Show tracked files and recent events")

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    config_path = Path(args.config)

    if args.command == "run":
        sys.exit(cmd_run(config_path, args.verbose))
    if args.command == "scan-once":
        sys.exit(cmd_scan_once(config_path, args.verbose))
    if args.command == "status":
        sys.exit(cmd_status(config_path))


if __name__ == "__main__":
    main()
