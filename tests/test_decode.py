import pandas as pd

from lp_history.index.abi import decode_get_reserves
from lp_history.index.decode import decode_log
from lp_history.state.fold import latest_reserves_from_events
from lp_history.state.v3_positions import in_range_liquidity, positions_from_events


def test_decode_sync_log(sync_logs):
    row = decode_log(sync_logs[0], sync_logs[0]["address"], "uniswap_v2")
    assert row is not None
    assert row["event_name"] == "Sync"
    assert row["protocol"] == "uniswap_v2"
    assert row["reserve0"] == "1000000000000"
    assert row["reserve1"] == "500000000000000000"
    assert row["block_number"] == 0x12C4B00


def test_decode_get_reserves():
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
    rows = [decode_log(log, log["address"], "uniswap_v2") for log in sync_logs]
    frame = pd.DataFrame(rows)
    reserves = latest_reserves_from_events(frame)
    assert reserves is not None
    assert reserves.block_number == 0x12C4B10
    assert reserves.reserve0 == 1_000_000_000_000
    assert reserves.reserve1 == 500_000_000_000_000_000


def test_decode_v3_mint(v3_mint_logs):
    row = decode_log(v3_mint_logs[0], v3_mint_logs[0]["address"], "uniswap_v3")
    assert row is not None
    assert row["event_name"] == "Mint"
    assert row["protocol"] == "uniswap_v3"
    assert row["owner"] == "0x2222222222222222222222222222222222222222"
    assert row["tick_lower"] == -10
    assert row["tick_upper"] == 10
    assert row["liquidity"] == "1000"
    assert row["amount0"] == "500"
    assert row["amount1"] == "600"


def test_v3_position_range_and_in_range(v3_mint_logs):
    rows = [decode_log(log, log["address"], "uniswap_v3") for log in v3_mint_logs]
    frame = pd.DataFrame(rows)
    positions = positions_from_events(frame)
    assert len(positions) == 1
    pos = positions[0]
    assert pos.range_width_ticks == 20
    assert in_range_liquidity(positions, current_tick=0) == 1000
    assert in_range_liquidity(positions, current_tick=10) == 0
    assert in_range_liquidity(positions, current_tick=-11) == 0
