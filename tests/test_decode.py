import pandas as pd

from lp_history.index.abi import decode_get_reserves, decode_log
from lp_history.state.fold import latest_reserves_from_events


def test_decode_sync_log(sync_logs):
    row = decode_log(sync_logs[0], sync_logs[0]["address"])
    assert row is not None
    assert row["event_name"] == "Sync"
    assert row["reserve0"] == "1000000000000"
    assert row["reserve1"] == "500000000000000000"
    assert row["block_number"] == 0x12C4B00


def test_decode_get_reserves():
    # Encoded (1000000000000, 500000000000000000, 1700000000)
    result = (
        "0x"
        "000000000000000000000000000000000000000000000000000000e8d4a51000"
        "00000000000000000000000000000000000000000000000006f05b59d3b20000"
        "000000000000000000000000000000000000000000000000000000006553f100"
    )
    r0, r1, ts = decode_get_reserves(result)
    assert r0 == 1_000_000_000_000
    assert r1 == 500_000_000_000_000_000
    assert ts == 1_700_000_000


def test_fold_latest_sync(sync_logs):
    rows = [decode_log(log, log["address"]) for log in sync_logs]
    frame = pd.DataFrame(rows)
    reserves = latest_reserves_from_events(frame)
    assert reserves is not None
    assert reserves.block_number == 0x12C4B10
    assert reserves.reserve0 == 1_000_000_000_000
    assert reserves.reserve1 == 500_000_000_000_000_000
