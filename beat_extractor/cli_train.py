from __future__ import annotations

import argparse
from pathlib import Path

from beat_extractor.ml import train_ranker_from_storage
from beat_extractor.paths import MODEL_PATH, ensure_data_dirs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the local tap-ranked beatmap model.")
    parser.add_argument("--out", type=Path, default=MODEL_PATH, help="Model output path.")
    args = parser.parse_args(argv)
    ensure_data_dirs()
    stats = train_ranker_from_storage(args.out)
    print(f"Wrote {stats['model_path']}")
    print(f"Rows: {stats['rows']} positive={stats['positives']} negative={stats['negatives']}")
    if stats["skipped_takes"]:
        print(f"Skipped takes with missing audio: {stats['skipped_takes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

