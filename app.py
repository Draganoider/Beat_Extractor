from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from beat_extractor.generator import generate_beatmap
from beat_extractor.io import atomic_write_json, safe_filename, sha256_file
from beat_extractor.preview import render_click_preview
from beat_extractor.schema import validate_beatmap
from beat_extractor.ui_state import events_from_editor, events_to_editor_rows


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
BEATMAP_DIR = DATA_DIR / "beatmaps"
RATING_DIR = DATA_DIR / "ratings"
TMP_DIR = DATA_DIR / "tmp"


def _ensure_data_dirs() -> None:
    for path in (UPLOAD_DIR, BEATMAP_DIR, RATING_DIR, TMP_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _save_upload(uploaded_file) -> Path:
    raw = uploaded_file.getvalue()
    digest = sha256_file(raw)
    name = f"{digest[:12]}_{safe_filename(uploaded_file.name)}"
    path = UPLOAD_DIR / name
    if not path.exists():
        path.write_bytes(raw)
    return path


def _load_local_path(raw_path: str) -> Path | None:
    if not raw_path.strip():
        return None
    path = Path(raw_path.strip()).expanduser()
    if path.exists() and path.is_file():
        return path
    st.error("File not found.")
    return None


def _beatmap_download_name(audio_path: Path) -> str:
    return f"{audio_path.stem}.beatmap.json"


def _save_rating(audio_path: Path, beatmap: dict, rating: int, notes: str) -> None:
    rating_path = RATING_DIR / "ratings.jsonl"
    record = {
        "audio": str(audio_path),
        "source_sha256": beatmap["source"]["sha256"],
        "beatmap_events": len(beatmap["events"]),
        "rating": rating,
        "notes": notes,
    }
    with rating_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def main() -> None:
    st.set_page_config(page_title="Beat Extractor", layout="wide")
    _ensure_data_dirs()

    st.title("Beat Extractor")

    with st.sidebar:
        uploaded = st.file_uploader("Song", type=["mp3", "wav", "flac", "ogg", "m4a"])
        local_path_text = st.text_input("Local path")
        target_density = st.slider("Density", min_value=60, max_value=180, value=115, step=5)
        min_spacing_ms = st.slider("Min spacing ms", min_value=100, max_value=350, value=180, step=10)
        tick_volume = st.slider("Tick volume", min_value=0, max_value=100, value=45, step=5)

    audio_path = None
    if uploaded is not None:
        audio_path = _save_upload(uploaded)
    else:
        audio_path = _load_local_path(local_path_text)

    if audio_path is None:
        st.info("Choose a song to begin.")
        return

    st.audio(str(audio_path))

    if "beatmap" not in st.session_state or st.session_state.get("audio_path") != str(audio_path):
        st.session_state.audio_path = str(audio_path)
        st.session_state.beatmap = None
        st.session_state.preview_path = None

    generate = st.button("Generate", type="primary")
    if generate:
        with st.spinner("Analyzing song"):
            beatmap = generate_beatmap(
                audio_path,
                target_events_per_minute=target_density,
                min_spacing_sec=min_spacing_ms / 1000.0,
            )
            validate_beatmap(beatmap)
            st.session_state.beatmap = beatmap
            st.session_state.preview_path = None

    beatmap = st.session_state.get("beatmap")
    if not beatmap:
        return

    summary_cols = st.columns(4)
    summary_cols[0].metric("BPM", f"{beatmap['analysis']['bpm']:.1f}")
    summary_cols[1].metric("Confidence", f"{beatmap['analysis']['confidence']:.2f}")
    summary_cols[2].metric("Events", len(beatmap["events"]))
    summary_cols[3].metric("Duration", f"{beatmap['source']['duration_sec']:.1f}s")

    rows = events_to_editor_rows(beatmap["events"])
    edited_rows = st.data_editor(
        rows,
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "enabled": st.column_config.CheckboxColumn("On"),
            "time_sec": st.column_config.NumberColumn("Time", min_value=0.0, step=0.001, format="%.3f"),
            "strength": st.column_config.NumberColumn("Strength", min_value=0.0, max_value=1.0, step=0.01),
            "confidence": st.column_config.NumberColumn("Confidence", min_value=0.0, max_value=1.0, step=0.01),
        },
    )

    beatmap["events"] = events_from_editor(edited_rows, beatmap["source"]["duration_sec"])
    validate_beatmap(beatmap)

    chart_data = pd.DataFrame(
        {
            "time_sec": [event["time_sec"] for event in beatmap["events"]],
            "strength": [event["strength"] for event in beatmap["events"]],
        }
    )
    if not chart_data.empty:
        st.scatter_chart(chart_data, x="time_sec", y="strength", height=220)

    preview_cols = st.columns([1, 3])
    if preview_cols[0].button("Render click preview"):
        with st.spinner("Rendering preview"):
            preview_path = TMP_DIR / f"{beatmap['source']['sha256'][:12]}_click_preview.wav"
            render_click_preview(audio_path, beatmap, preview_path, click_gain=tick_volume / 100.0)
            st.session_state.preview_path = str(preview_path)

    preview_path = st.session_state.get("preview_path")
    if preview_path and Path(preview_path).exists():
        preview_cols[1].audio(preview_path)

    rating_cols = st.columns([1, 3, 1])
    rating = rating_cols[0].slider("Rating", 1, 5, 4)
    notes = rating_cols[1].text_input("Notes")

    output_path = BEATMAP_DIR / _beatmap_download_name(audio_path)
    payload = json.dumps(beatmap, indent=2, ensure_ascii=True)

    if rating_cols[2].button("Save"):
        atomic_write_json(output_path, beatmap)
        _save_rating(audio_path, beatmap, rating, notes)
        st.success(f"Saved {output_path}")

    st.download_button(
        "Download JSON",
        payload,
        file_name=_beatmap_download_name(audio_path),
        mime="application/json",
    )


if __name__ == "__main__":
    main()
