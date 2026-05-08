from __future__ import annotations

import numpy as np
import soundfile as sf

from auto_determining.preview import render_click_preview


def test_click_preview_renders_audible_ticks(tmp_path) -> None:
    sample_rate = 22050
    audio_path = tmp_path / "silent.wav"
    output_path = tmp_path / "preview.wav"
    samples = np.zeros(sample_rate * 2, dtype=np.float32)
    sf.write(audio_path, samples, sample_rate)

    beatmap = {
        "events": [
            {"time_sec": 0.5, "strength": 1.0},
            {"time_sec": 1.0, "strength": 0.8},
        ]
    }
    render_click_preview(audio_path, beatmap, output_path, sample_rate=sample_rate)

    rendered, rendered_rate = sf.read(output_path)
    tick_window = rendered[int(0.5 * sample_rate) : int(0.56 * sample_rate)]

    assert output_path.exists()
    assert rendered_rate == sample_rate
    assert float(np.max(np.abs(tick_window))) > 0.2


