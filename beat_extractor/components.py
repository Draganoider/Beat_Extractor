from __future__ import annotations

import streamlit as st


_TAP_RECORDER_JS = r"""
export default function({ data, parentElement, setStateValue }) {
  const mode = data.mode || "record";
  const title = mode === "calibrate" ? "Latency calibration" : "Tap recording";
  parentElement.innerHTML = `
    <div class="tap-box">
      <div class="tap-title">${title}</div>
      <div class="tap-row">
        <button id="start">Start</button>
        <button id="stop">Stop and send</button>
        <button id="reset">Reset</button>
        <span id="status">Idle</span>
      </div>
      <div id="audioMount"></div>
      <div id="tapPad" tabindex="0">Tap here with mouse, or press Space</div>
      <div class="tap-count"><span id="count">0</span> taps captured</div>
    </div>
  `;

  const startButton = parentElement.querySelector("#start");
  const stopButton = parentElement.querySelector("#stop");
  const resetButton = parentElement.querySelector("#reset");
  const status = parentElement.querySelector("#status");
  const count = parentElement.querySelector("#count");
  const tapPad = parentElement.querySelector("#tapPad");
  const audioMount = parentElement.querySelector("#audioMount");

  let rawTaps = [];
  let expectedTimes = [];
  let running = false;
  let audio = null;
  let audioContext = null;
  let calibrationStart = 0;
  let finishTimer = null;

  if (mode === "record") {
    audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "auto";
    audio.src = data.audio_data_url || "";
    audio.style.width = "100%";
    audioMount.appendChild(audio);
    audio.addEventListener("ended", finish);
  }

  function setStatus(text) {
    status.textContent = text;
  }

  function updateCount() {
    count.textContent = String(rawTaps.length);
  }

  function capture(inputKind) {
    if (!running) return;
    let timeSec = 0;
    if (mode === "calibrate") {
      timeSec = audioContext.currentTime - calibrationStart;
    } else {
      timeSec = audio.currentTime;
    }
    if (timeSec < -0.25) return;
    rawTaps.push({ time_sec: Math.max(0, Number(timeSec.toFixed(6))), input_kind: inputKind });
    updateCount();
  }

  function keyHandler(event) {
    if (event.code !== "Space" || event.repeat) return;
    event.preventDefault();
    capture("spacebar");
  }

  function mouseHandler(event) {
    event.preventDefault();
    capture("mouse");
  }

  function scheduleClick(context, time) {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "square";
    oscillator.frequency.value = 1800;
    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(0.45, time + 0.003);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.055);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start(time);
    oscillator.stop(time + 0.06);
  }

  async function start() {
    rawTaps = [];
    expectedTimes = [];
    updateCount();
    running = true;
    tapPad.focus();
    window.addEventListener("keydown", keyHandler);
    tapPad.addEventListener("pointerdown", mouseHandler);

    if (mode === "calibrate") {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      await audioContext.resume();
      const bpm = data.bpm || 100;
      const clickCount = data.click_count || 12;
      const interval = 60 / bpm;
      calibrationStart = audioContext.currentTime + 0.55;
      for (let index = 0; index < clickCount; index += 1) {
        const expected = index * interval;
        expectedTimes.push(Number(expected.toFixed(6)));
        scheduleClick(audioContext, calibrationStart + expected);
      }
      const totalMs = Math.ceil((clickCount * interval + 0.8) * 1000);
      finishTimer = window.setTimeout(finish, totalMs);
      setStatus("Running metronome");
    } else {
      audio.currentTime = 0;
      await audio.play();
      setStatus("Recording");
    }
  }

  function finish() {
    if (!running) return;
    running = false;
    window.removeEventListener("keydown", keyHandler);
    tapPad.removeEventListener("pointerdown", mouseHandler);
    if (finishTimer) window.clearTimeout(finishTimer);
    if (audio) audio.pause();
    setStatus("Sent to Python");
    setStateValue("result", {
      mode,
      raw_taps: rawTaps,
      expected_times: expectedTimes,
      input_counts: rawTaps.reduce((acc, tap) => {
        acc[tap.input_kind] = (acc[tap.input_kind] || 0) + 1;
        return acc;
      }, {}),
      ended_at_ms: Date.now()
    });
  }

  function reset() {
    rawTaps = [];
    expectedTimes = [];
    updateCount();
    setStatus("Reset");
  }

  startButton.addEventListener("click", start);
  stopButton.addEventListener("click", finish);
  resetButton.addEventListener("click", reset);

  return () => {
    running = false;
    window.removeEventListener("keydown", keyHandler);
    tapPad.removeEventListener("pointerdown", mouseHandler);
    if (finishTimer) window.clearTimeout(finishTimer);
    if (audio) audio.pause();
    if (audioContext) audioContext.close();
  };
}
"""


_TAP_RECORDER_CSS = """
.tap-box {
  border: 1px solid color-mix(in srgb, var(--border-color, #d4d4d8), transparent 20%);
  border-radius: 8px;
  padding: 14px;
  background: var(--background-color, #fff);
}
.tap-title {
  font-weight: 700;
  margin-bottom: 10px;
}
.tap-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
button {
  border: 1px solid #8b8b95;
  border-radius: 6px;
  background: #ffffff;
  color: #15151a;
  padding: 7px 10px;
  cursor: pointer;
}
#status {
  color: #555a66;
}
#tapPad {
  display: grid;
  place-items: center;
  min-height: 112px;
  margin-top: 12px;
  border: 2px dashed #8791a5;
  border-radius: 8px;
  background: #f7f8fb;
  color: #1f2530;
  font-weight: 700;
  outline: none;
  user-select: none;
}
#tapPad:focus {
  border-color: #2f70d0;
  box-shadow: 0 0 0 3px rgba(47, 112, 208, 0.18);
}
.tap-count {
  margin-top: 8px;
  font-size: 0.92rem;
  color: #555a66;
}
"""


_tap_recorder = st.components.v2.component(
    "tap_training_recorder",
    html="<div></div>",
    css=_TAP_RECORDER_CSS,
    js=_TAP_RECORDER_JS,
)


def _noop_component_callback() -> None:
    pass


def tap_recorder(
    *,
    mode: str,
    key: str,
    audio_data_url: str | None = None,
    bpm: int = 100,
    click_count: int = 12,
):
    return _tap_recorder(
        key=key,
        data={
            "mode": mode,
            "audio_data_url": audio_data_url,
            "bpm": bpm,
            "click_count": click_count,
        },
        default={"result": None},
        height=360,
        on_result_change=_noop_component_callback,
    )
