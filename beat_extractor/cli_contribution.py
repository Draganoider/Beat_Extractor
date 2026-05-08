from __future__ import annotations

import argparse
from pathlib import Path

from beat_extractor.contributions import export_contribution_bundle, import_contribution_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export or import Beat Extractor contribution bundles.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export approved takes and referenced audio files.")
    export_parser.add_argument("--contributor", default="friend", help="Contributor name used in the bundle filename.")
    export_parser.add_argument("--out", type=Path, help="Output .zip path.")
    export_parser.add_argument("--include-rejected", action="store_true", help="Also include rejected takes.")

    import_parser = subparsers.add_parser("import", help="Import a contribution bundle.")
    import_parser.add_argument("bundle", type=Path, help="Contribution .zip file.")

    args = parser.parse_args(argv)
    if args.command == "export":
        path = export_contribution_bundle(
            contributor_id=args.contributor,
            output_path=args.out,
            include_rejected=args.include_rejected,
        )
        print(f"Wrote {path}")
        return 0

    stats = import_contribution_bundle(args.bundle)
    print(f"Imported audio files: {stats['imported_audio']}")
    print(f"Imported takes: {stats['imported_takes']}")
    print(f"Skipped takes: {stats['skipped_takes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

