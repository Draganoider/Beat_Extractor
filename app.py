from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from auto_determining.io import atomic_write_json, safe_filename, sha256_file
from auto_determining.preview import render_click_preview
from auto_determining.schema import validate_beatmap

from beat_extractor.ai_generator import beatmap_from_cleaned_events, generate_ai_beatmap
from beat_extractor.components import tap_recorder
from beat_extractor.media import audio_data_url
from beat_extractor.ml import list_model_runs, set_active_model, train_ranker_from_storage
from beat_extractor.paths import BEATMAP_DIR, MODEL_INDEX_PATH, TMP_DIR, UPLOAD_DIR, ensure_data_dirs
from beat_extractor.storage import build_training_take, iter_training_takes, load_profile, save_profile, save_training_take
from beat_extractor.taps import calibration_is_ready, clean_taps, estimate_calibration


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


def _selected_audio() -> Path | None:
    with st.sidebar:
        uploaded = st.file_uploader("Song", type=["mp3", "wav", "flac", "ogg", "m4a"])
        local_path_text = st.text_input("Local path")
    return _save_upload(uploaded) if uploaded is not None else _load_local_path(local_path_text)


def _store_component_result(key: str, component_result) -> dict | None:
    result = component_result.get("result") if component_result else None
    if result:
        st.session_state[key] = result
    return st.session_state.get(key)


def _event_table(beatmap: dict) -> None:
    chart_data = pd.DataFrame(
        {
            "time_sec": [event["time_sec"] for event in beatmap["events"]],
            "confidence": [event["confidence"] for event in beatmap["events"]],
        }
    )
    if not chart_data.empty:
        st.scatter_chart(chart_data, x="time_sec", y="confidence", height=220)


def _render_preview(audio_path: Path, beatmap: dict, name: str, tick_volume: int) -> Path:
    preview_path = TMP_DIR / f"{beatmap['source']['sha256'][:12]}_{name}.wav"
    render_click_preview(audio_path, beatmap, preview_path, click_gain=tick_volume / 100.0)
    return preview_path


def main() -> None:
    st.set_page_config(page_title="Tap-Trained Beatmap AI", layout="wide")
    ensure_data_dirs()
    st.title("Tap-Trained Beatmap AI")

    audio_path = _selected_audio()
    tick_volume = st.sidebar.slider("Tick volume", min_value=0, max_value=100, value=45, step=5)
    target_density = st.sidebar.slider("AI density", min_value=60, max_value=180, value=115, step=5)
    min_spacing_ms = st.sidebar.slider("AI min spacing ms", min_value=100, max_value=350, value=180, step=10)

    profile = load_profile()
    calibration = profile.get("calibration", {})
    if audio_path is not None:
        st.audio(str(audio_path))

    calibrate_tab, record_tab, review_tab, train_tab, generate_tab = st.tabs(
        ["Calibrate", "Record", "Review", "Train", "Generate"]
    )

    with calibrate_tab:
        st.subheader("Required latency calibration")
        cols = st.columns(2)
        cols[0].metric("Spacebar latency", _format_latency(calibration.get("spacebar_latency_ms")))
        cols[1].metric("Mouse latency", _format_latency(calibration.get("mouse_latency_ms")))
        st.caption("Start the metronome, tap with both Space and mouse on the pad, then save calibration.")
        component_result = tap_recorder(mode="calibrate", key="latency-calibrator", bpm=100, click_count=12)
        latest = _store_component_result("latest_calibration_result", component_result)
        if latest:
            counts = latest.get("input_counts", {})
            st.write(f"Latest capture: {counts.get('spacebar', 0)} spacebar taps, {counts.get('mouse', 0)} mouse taps")
            if st.button("Save calibration", type="primary"):
                estimated = estimate_calibration(latest.get("expected_times", []), latest.get("raw_taps", []))
                if not calibration_is_ready(estimated):
                    st.error("Tap with both Space and mouse during calibration before saving.")
                else:
                    profile["calibration"] = estimated
                    save_profile(profile)
                    st.success("Calibration saved.")
                    st.rerun()

    with record_tab:
        st.subheader("Record a human tap take")
        if audio_path is None:
            st.info("Choose a song in the sidebar first.")
        elif not calibration_is_ready(calibration):
            st.warning("Save calibration for both Space and mouse first.")
        else:
            component_result = tap_recorder(
                mode="record",
                key=f"tap-recorder-{sha256_file(audio_path)[:12]}",
                audio_data_url=audio_data_url(audio_path),
            )
            latest = _store_component_result("latest_recording_result", component_result)
            if latest:
                raw_taps = latest.get("raw_taps", [])
                cleaned = clean_taps(raw_taps, calibration, _duration_from_audio(audio_path))
                st.write(f"Latest recording: {len(raw_taps)} raw taps, {len(cleaned)} cleaned events")
                if st.button("Create review draft", type="primary"):
                    st.session_state.review_draft = {
                        "audio_path": str(audio_path),
                        "raw_taps": raw_taps,
                        "cleaned_events": cleaned,
                        "calibration": calibration,
                    }
                    st.success("Draft ready in Review.")

    with review_tab:
        st.subheader("Review and approve training take")
        draft = st.session_state.get("review_draft")
        if not draft:
            st.info("Record a take first.")
        else:
            draft_audio_path = Path(draft["audio_path"])
            beatmap = beatmap_from_cleaned_events(draft_audio_path, draft["cleaned_events"])
            validate_beatmap(beatmap)
            st.write(f"Cleaned events: {len(beatmap['events'])}")
            _event_table(beatmap)
            if st.button("Render human-tap preview"):
                st.session_state.review_preview_path = str(_render_preview(draft_audio_path, beatmap, "human_taps", tick_volume))
            preview_path = st.session_state.get("review_preview_path")
            if preview_path and Path(preview_path).exists():
                st.audio(preview_path)
            rating = st.slider("Take rating", 1, 5, 5)
            notes = st.text_input("Notes")
            action_cols = st.columns(2)
            if action_cols[0].button("Approve take", type="primary"):
                take = build_training_take(
                    draft_audio_path,
                    raw_taps=draft["raw_taps"],
                    cleaned_events=draft["cleaned_events"],
                    calibration=draft["calibration"],
                    rating=rating,
                    notes=notes,
                    status="approved",
                )
                path = save_training_take(take)
                st.success(f"Saved approved take: {path}")
            if action_cols[1].button("Reject take"):
                take = build_training_take(
                    draft_audio_path,
                    raw_taps=draft["raw_taps"],
                    cleaned_events=draft["cleaned_events"],
                    calibration=draft["calibration"],
                    rating=rating,
                    notes=notes,
                    status="rejected",
                )
                path = save_training_take(take)
                st.warning(f"Saved rejected take: {path}")

    with train_tab:
        st.subheader("Train local ranker")
        approved = iter_training_takes(status="approved")
        st.metric("Approved takes", len(approved))
        model_runs = list_model_runs()
        if MODEL_INDEX_PATH.exists():
            st.success(f"Active model pointer exists: {MODEL_INDEX_PATH}")
        if st.button("Train model", type="primary"):
            try:
                stats = train_ranker_from_storage()
            except ValueError as error:
                st.error(str(error))
            else:
                st.success(f"Trained model run {stats['run_id']} with {stats['rows']} rows.")
                st.json(stats)
                st.rerun()
        if model_runs:
            st.write("Model history")
            history = pd.DataFrame(
                [
                    {
                        "active": run.get("active", False),
                        "run_id": run["run_id"],
                        "rows": run["rows"],
                        "positives": run["positives"],
                        "negatives": run["negatives"],
                        "accuracy": round(float(run["train_accuracy"]), 4),
                        "created_at": run["created_at"],
                    }
                    for run in model_runs
                ]
            )
            st.dataframe(history, hide_index=True, use_container_width=True)
            selected_run = st.selectbox("Model run", [run["run_id"] for run in model_runs])
            if st.button("Activate selected model"):
                activated = set_active_model(selected_run)
                st.success(f"Activated {activated['run_id']}")
                st.rerun()

    with generate_tab:
        st.subheader("Generate with trained AI")
        if audio_path is None:
            st.info("Choose a song in the sidebar first.")
        else:
            if st.button("Generate beatmap", type="primary"):
                with st.spinner("Generating beatmap"):
                    beatmap = generate_ai_beatmap(
                        audio_path,
                        target_events_per_minute=target_density,
                        min_spacing_sec=min_spacing_ms / 1000.0,
                    )
                    validate_beatmap(beatmap)
                    st.session_state.generated_ai_beatmap = beatmap
            beatmap = st.session_state.get("generated_ai_beatmap")
            if beatmap:
                st.write(f"Generator: `{beatmap.get('generator', 'unknown')}`")
                st.metric("Events", len(beatmap["events"]))
                _event_table(beatmap)
                preview_cols = st.columns([1, 3])
                if preview_cols[0].button("Render AI preview"):
                    st.session_state.ai_preview_path = str(_render_preview(audio_path, beatmap, "ai_preview", tick_volume))
                preview_path = st.session_state.get("ai_preview_path")
                if preview_path and Path(preview_path).exists():
                    preview_cols[1].audio(preview_path)
                output_path = BEATMAP_DIR / f"{audio_path.stem}.beatmap.json"
                payload = json.dumps(beatmap, indent=2, ensure_ascii=True)
                if st.button("Save AI beatmap"):
                    atomic_write_json(output_path, beatmap)
                    st.success(f"Saved {output_path}")
                st.download_button("Download JSON", payload, file_name=output_path.name, mime="application/json")


def _duration_from_audio(audio_path: Path) -> float:
    from auto_determining.audio import load_audio

    return load_audio(audio_path).duration_sec


def _format_latency(value) -> str:
    return "missing" if value is None else f"{float(value):.1f} ms"


if __name__ == "__main__":
    main()
