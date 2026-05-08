# Beat Extractor

Automatic beatmap extraction prototype for rhythm games. The first version turns a song into an engine-neutral JSON file containing timed hit events with strength and confidence values.

## Setup

Install Python 3.12 from python.org, then run:

```powershell
scripts\setup.cmd
```

This creates `.venv` and installs the project dependencies.

## Generate a Beatmap

```powershell
scripts\analyze.cmd "path\to\song.mp3" --out "data\beatmaps\song.beatmap.json"
```

## Preview and Edit

```powershell
scripts\run_ui.cmd
```

The local Streamlit app can upload/select songs, generate markers, render a tick-overlay audio preview, edit event timing/enabled state, save JSON, and store a quality rating for later tuning.

## Test

```powershell
scripts\test.cmd
```

The `.cmd` wrappers run the PowerShell scripts with a one-off execution-policy bypass. If you prefer direct PowerShell, use `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`.

## Notes

The required v1 stack is commercial-friendly and Windows-friendly. Research-grade or license-sensitive backends such as Essentia, madmom, or stem-separation models can be added later as optional plugins, not as required runtime dependencies.
