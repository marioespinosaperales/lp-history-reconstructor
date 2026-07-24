from lp_history.ml.clear_exit_model import (
    build_report,
    train_clear_exit_model,
    write_report,
)
from lp_history.ml.features import FEATURE_COLUMNS, synthesize_positions, xy_from_frame


def test_synthetic_features_and_model(tmp_path):
    frame = synthesize_positions(n=200, seed=3)
    assert set(FEATURE_COLUMNS).issubset(frame.columns)
    x, y = xy_from_frame(frame)
    assert x.shape[0] == 200
    assert set(y.tolist()) == {0, 1}

    result = train_clear_exit_model(frame, seed=3)
    assert result.metrics["f1_clear_exit"] >= 0.65
    assert result.metrics["accuracy"] >= 0.75

    report = build_report(result)
    out = write_report(report, artifacts_dir=tmp_path)
    assert out.exists()
    assert "clear-exit" in out.read_text(encoding="utf-8").lower()
