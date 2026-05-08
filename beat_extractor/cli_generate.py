from __future__ import annotations

import argparse
from pathlib import Path

from auto_determining.io import atomic_write_json

from beat_extractor.ai_generator import generate_ai_beatmap
from beat_extractor.paths import MODEL_PATH, ensure_data_dirs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a beatmap with the local ML ranker, or fallback detector.")
    parser.add_argument("song", type=Path, help="Audio file to analyze.")
    parser.add_argument("--out", type=Path, help="Output beatmap JSON path.")
    parser.add_argument("--model", type=Path, default=MODEL_PATH, help="Trained model path.")
    parser.add_argument("--density", type=int, default=115, help="Target events per minute.")
    parser.add_argument("--min-spacing", type=float, default=0.18, help="Minimum seconds between events.")
    args = parser.parse_args(argv)
    ensure_data_dirs()
    output = args.out or Path("data") / "beatmaps" / f"{args.song.stem}.beatmap.json"
    beatmap = generate_ai_beatmap(
        args.song,
        model_path=args.model,
        target_events_per_minute=args.density,
        min_spacing_sec=args.min_spacing,
    )
    atomic_write_json(output, beatmap)
    print(f"Wrote {output}")
    print(f"Generator: {beatmap.get('generator', 'unknown')}")
    print(f"Events: {len(beatmap['events'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

