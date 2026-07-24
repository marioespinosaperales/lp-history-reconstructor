from lp_history.evals.scorecard import (
    VerifyCheck,
    build_scorecard,
    classify_verify_status,
    render_markdown,
    summarize_verify_results,
    write_scorecard,
)


def test_classify_verify_status():
    assert classify_verify_status("PASS reserves match at block 1", True) == "exact"
    assert (
        classify_verify_status("SMOKE_OK PARTIAL at tick 1: reconstructed L=1", True)
        == "partial_or_smoke"
    )
    assert classify_verify_status("FAIL at tick 1: reconstructed L=9 > on-chain L=1", False) == (
        "fail"
    )


def test_summarize_and_render(tmp_path):
    checks = [
        VerifyCheck("v3", "partial_or_smoke", True, "SMOKE_OK PARTIAL at tick 1"),
        VerifyCheck("v2", "exact", True, "PASS reserves match at block 1"),
        VerifyCheck("bad", "fail", False, "FAIL at block 1"),
    ]
    summary = summarize_verify_results(checks)
    assert summary == {
        "exact": 1,
        "partial_or_smoke": 1,
        "fail": 1,
        "skipped": 0,
        "total": 3,
    }
    scorecard = build_scorecard(
        checks,
        duckdb_path=tmp_path / "missing.duckdb",
        lookback_blocks=2500,
    )
    assert any("lookback_blocks" in c for c in scorecard.caveats)
    md = render_markdown(scorecard)
    assert "# LP history QC scorecard" in md
    assert "partial_or_smoke" in md
    out = write_scorecard(scorecard, artifacts_dir=tmp_path)
    assert out.exists()
    assert (tmp_path / "qc_scorecard.json").exists()
