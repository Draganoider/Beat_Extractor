from __future__ import annotations

from beat_extractor.dataset import label_candidate_rows


def test_dataset_labeling_marks_candidates_near_human_taps() -> None:
    rows = [{"time_sec": 0.5}, {"time_sec": 1.0}, {"time_sec": 1.5}]

    labels = label_candidate_rows(rows, [0.53, 1.49], tolerance_sec=0.08)

    assert labels == [1, 0, 1]

