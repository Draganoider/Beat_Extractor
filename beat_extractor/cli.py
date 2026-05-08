from __future__ import annotations

import argparse
from pathlib import Path

from beat_extractor.generator import generate_beatmap
from beat_extractor.io import atomic_write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a rhythm-game beatmap JSON from a song.")
    parser.add_argument("song", type=Path, help="Audio file to analyze.")
    parser.add_argument("--out", type=Path, help="Output beatmap JSON path.")
    parser.add_argument("--density", type=int, default=115, help="Target events per minute.")
    parser.add_argument("--min-spacing", type=float, default=0.18, help="Minimum seconds between events.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.out
    if output is None:
        output = Path("data") / "beatmaps" / f"{args.song.stem}.beatmap.json"

    beatmap = generate_beatmap(
        args.song,
        target_events_per_minute=args.density,
        min_spacing_sec=args.min_spacing,
    )
    atomic_write_json(output, beatmap)
    print(f"Wrote {output}")
    print(f"Events: {len(beatmap['events'])}")
    print(f"BPM: {beatmap['analysis']['bpm']:.2f}")
    print(f"Confidence: {beatmap['analysis']['confidence']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

