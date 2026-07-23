import json
from pathlib import Path

import pandas as pd

from lp_history.index.npm_abi import decode_log
from lp_history.state.npm_wallets import liquidity_by_token_id, wallet_by_token_id

FIXTURES = Path(__file__).parent / "fixtures"


def test_decode_npm_transfer_and_increase():
    logs = json.loads((FIXTURES / "npm_logs.json").read_text(encoding="utf-8"))
    transfer = decode_log(logs[0], logs[0]["address"])
    assert transfer is not None
    assert transfer["event_name"] == "Transfer"
    assert transfer["token_id"] == "123"
    assert transfer["to_address"] == "0xaAaAaAaaAaAaAaaAaAAAAAAAAaaaAaAaAaaAaaAa"

    increase = decode_log(logs[1], logs[1]["address"])
    assert increase is not None
    assert increase["event_name"] == "IncreaseLiquidity"
    assert increase["token_id"] == "123"
    assert increase["liquidity"] == "5000"


def test_wallet_and_liquidity_maps():
    logs = json.loads((FIXTURES / "npm_logs.json").read_text(encoding="utf-8"))
    rows = [decode_log(log, log["address"]) for log in logs]
    frame = pd.DataFrame(rows)
    owners = wallet_by_token_id(frame)
    liqs = liquidity_by_token_id(frame)
    assert owners[123] == "0xaAaAaAaaAaAaAaaAaAAAAAAAAaaaAaAaAaaAaaAa"
    assert liqs[123] == 5000
