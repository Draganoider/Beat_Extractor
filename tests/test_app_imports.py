from __future__ import annotations

import importlib


def test_main_app_imports_cleanly() -> None:
    importlib.import_module("app")

