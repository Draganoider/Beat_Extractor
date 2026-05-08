# Beat Extractor

Local tap-trained beatmap AI demo for rhythm-game timing. The current app focuses on collecting calibrated human taps, approving good takes, training a local ML ranker, and generating `beatmap-v1` JSON for game integration.

## Setup

For friends, the easiest path is to download/extract the project and double-click:

```powershell
START_HERE.cmd
```

That creates the local environment, installs dependencies, and starts the app.

Manual setup:

```powershell
scripts\setup.cmd
```

## Run The Tap Training App

```powershell
scripts\run_ui.cmd
```

Workflow:

1. Choose or upload a song.
2. Calibrate both Space and mouse latency.
3. Record a tap take using Space and/or mouse.
4. Review the click-overlay preview.
5. Approve the take.
6. Train the local model.
7. Generate an AI beatmap and preview it with ticks.

Training data is stored locally under ignored `data/training/`. Every trained model is saved as a versioned run under `data/models/runs/`, and `data/models/current_model.json` points to the active model used for generation.

## Friend Contributions

Friends should not send the whole `data/` folder. It contains temp previews, local models, and machine-specific files.

Instead, they should export a contribution bundle from the app's `Share` tab or run:

```powershell
scripts\export_contribution.cmd --contributor "friend_name"
```

The bundle is saved under `data/contributions/` and includes approved tap takes plus the referenced song files. They can send you that `.zip`.

You import a friend's bundle with the app's `Share` tab or:

```powershell
scripts\import_contribution.cmd "path\to\bundle.contribution.zip"
```

Then train a new local model.

## Commands

Generate with trained AI, falling back to the automatic detector when no model exists:

```powershell
scripts\generate_ai.cmd "path\to\song.mp3" --out "data\beatmaps\song.beatmap.json"
```

Train from approved local takes:

```powershell
scripts\train_model.cmd
```

Run the old deterministic detector UI:

```powershell
scripts\run_auto_determining.cmd
```

Run the old deterministic detector CLI:

```powershell
scripts\analyze_auto.cmd "path\to\song.mp3" --out "data\beatmaps\song.auto.beatmap.json"
```

## Test

```powershell
scripts\test.cmd
```

The `.cmd` wrappers run the PowerShell scripts with a one-off execution-policy bypass.
