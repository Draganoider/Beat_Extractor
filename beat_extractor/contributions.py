from __future__ import annotations

import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from auto_determining.io import atomic_write_json, safe_filename, sha256_file

from beat_extractor.paths import CONTRIBUTIONS_DIR, TAKES_DIR, UPLOAD_DIR, ensure_data_dirs
from beat_extractor.storage import iter_training_takes
from beat_extractor.training_schema import validate_training_take


BUNDLE_VERSION = "contribution-bundle-v1"


def export_contribution_bundle(
    *,
    contributor_id: str = "friend",
    output_path: str | Path | None = None,
    include_rejected: bool = False,
) -> Path:
    ensure_data_dirs()
    statuses = None if include_rejected else "approved"
    takes = iter_training_takes(status=statuses)
    if not takes:
        raise ValueError("No training takes found to export.")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = Path(output_path) if output_path else CONTRIBUTIONS_DIR / f"{timestamp}_{safe_filename(contributor_id)}.contribution.zip"
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": BUNDLE_VERSION,
        "contributor_id": contributor_id,
        "created_at": datetime.now(UTC).isoformat(),
        "include_rejected": include_rejected,
        "takes": [],
        "missing_audio": [],
    }

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for take in takes:
            validate_training_take(take)
            audio_path = Path(take["source"]["path"])
            song_hash = take["source"]["sha256"]
            take_id = take["take_id"]
            take_arcname = f"takes/{song_hash[:16]}/{take_id}.training.json"
            archive.writestr(take_arcname, json.dumps(take, indent=2, ensure_ascii=True))

            audio_arcname = None
            if audio_path.exists():
                audio_name = f"{song_hash[:12]}_{safe_filename(take['source']['filename'])}"
                audio_arcname = f"uploads/{audio_name}"
                archive.write(audio_path, audio_arcname)
            else:
                manifest["missing_audio"].append({"take_id": take_id, "path": str(audio_path)})

            manifest["takes"].append(
                {
                    "take_id": take_id,
                    "status": take["status"],
                    "song_sha256": song_hash,
                    "filename": take["source"]["filename"],
                    "duration_sec": take["source"]["duration_sec"],
                    "audio_file": audio_arcname,
                    "take_file": take_arcname,
                }
            )

        archive.writestr("contribution_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=True))

    return output


def import_contribution_bundle(bundle_path: str | Path) -> dict:
    ensure_data_dirs()
    bundle = Path(bundle_path)
    if not bundle.exists():
        raise FileNotFoundError(bundle)

    imported_audio: dict[str, Path] = {}
    imported_takes = 0
    skipped_takes = 0

    with zipfile.ZipFile(bundle, "r") as archive:
        manifest = json.loads(archive.read("contribution_manifest.json").decode("utf-8"))
        if manifest.get("version") != BUNDLE_VERSION:
            raise ValueError("Unsupported contribution bundle version.")

        for item in manifest.get("takes", []):
            audio_arcname = item.get("audio_file")
            if audio_arcname:
                target_audio = UPLOAD_DIR / Path(audio_arcname).name
                if not target_audio.exists():
                    with archive.open(audio_arcname) as source, target_audio.open("wb") as target:
                        shutil.copyfileobj(source, target)
                imported_audio[item["song_sha256"]] = target_audio

        for item in manifest.get("takes", []):
            raw_take = json.loads(archive.read(item["take_file"]).decode("utf-8"))
            audio_path = imported_audio.get(raw_take["source"]["sha256"])
            if audio_path is None:
                skipped_takes += 1
                continue
            if sha256_file(audio_path) != raw_take["source"]["sha256"]:
                skipped_takes += 1
                continue

            raw_take["source"]["path"] = str(audio_path)
            validate_training_take(raw_take)
            take_dir = TAKES_DIR / raw_take["source"]["sha256"][:16]
            take_path = take_dir / f"{raw_take['take_id']}.training.json"
            if take_path.exists():
                skipped_takes += 1
                continue
            atomic_write_json(take_path, raw_take)
            imported_takes += 1

    return {
        "bundle": str(bundle),
        "imported_audio": len(imported_audio),
        "imported_takes": imported_takes,
        "skipped_takes": skipped_takes,
    }

