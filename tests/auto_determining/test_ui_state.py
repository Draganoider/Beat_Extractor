from __future__ import annotations

import importlib

from auto_determining.ui_state import events_from_editor, events_to_editor_rows


def test_app_imports_cleanly() -> None:
    importlib.import_module("auto_determining_app")


def test_editor_roundtrip_preserves_user_edits() -> None:
    events = [
        {
            "id": "evt_000001",
            "time_sec": 1.0,
            "type": "hit",
            "strength": 0.8,
            "confidence": 0.7,
            "source": "beat",
            "edited": False,
        }
    ]

    rows = events_to_editor_rows(events)
    rows.loc[0, "time_sec"] = 1.25
    rows.loc[0, "enabled"] = True
    exported = events_from_editor(rows, duration_sec=3.0)

    assert exported[0]["time_sec"] == 1.25
    assert exported[0]["edited"] is True
    assert exported[0]["id"] == "evt_000001"


