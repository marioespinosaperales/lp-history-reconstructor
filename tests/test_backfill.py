import json

import httpx
import respx

from lp_history.index.backfill import backfill_pool
from lp_history.load.checkpoint import load_checkpoint
from lp_history.load.parquet import read_all_events
from lp_history.rpc.client import RpcClient
from lp_history.state.fold import latest_reserves_for_pool
from lp_history.verify.check import verify_pool


@respx.mock
def test_backfill_checkpoint_and_verify(pool, pipeline, sync_logs):
    tip = 0x12C4B10
    rpc_url = "https://eth-mainnet.example/v2/test"

    def rpc_side_effect(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method = body["method"]
        req_id = body["id"]
        if method == "eth_blockNumber":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": req_id, "result": hex(tip)})
        if method == "eth_getLogs":
            params = body["params"][0]
            start = int(params["fromBlock"], 16)
            end = int(params["toBlock"], 16)
            filtered = [
                log
                for log in sync_logs
                if start <= int(log["blockNumber"], 16) <= end
            ]
            return httpx.Response(
                200, json={"jsonrpc": "2.0", "id": req_id, "result": filtered}
            )
        if method == "eth_call":
            # getReserves matching the Sync fixture
            result = (
                "0x"
                "000000000000000000000000000000000000000000000000000000e8d4a51000"
                "00000000000000000000000000000000000000000000000006f05b59d3b20000"
                "000000000000000000000000000000000000000000000000000000006553f100"
            )
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": req_id, "result": result})
        return httpx.Response(400, json={"jsonrpc": "2.0", "id": req_id, "error": "unknown"})

    respx.post(rpc_url).mock(side_effect=rpc_side_effect)

    rpc = RpcClient(rpc_url, max_retries=0)
    stats = backfill_pool(rpc, pool, pipeline)

    assert stats["events"] == 2
    assert load_checkpoint(pipeline.checkpoint_dir, pool.address) == tip
    events = read_all_events(pipeline.data_dir, pool.address)
    assert len(events) == 2
    assert latest_reserves_for_pool(pipeline.data_dir, pool.address) is not None

    result = verify_pool(rpc, pipeline.data_dir, pool.address)
    assert result.ok, result.message


@respx.mock
def test_verify_fails_on_mismatch(pool, pipeline, sync_logs):
    tip = 0x12C4B10
    rpc_url = "https://eth-mainnet.example/v2/test"

    def rpc_side_effect(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method = body["method"]
        req_id = body["id"]
        if method == "eth_blockNumber":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": req_id, "result": hex(tip)})
        if method == "eth_getLogs":
            params = body["params"][0]
            start = int(params["fromBlock"], 16)
            end = int(params["toBlock"], 16)
            filtered = [
                log
                for log in sync_logs
                if start <= int(log["blockNumber"], 16) <= end
            ]
            return httpx.Response(
                200, json={"jsonrpc": "2.0", "id": req_id, "result": filtered}
            )
        if method == "eth_call":
            # Wrong reserves
            result = (
                "0x"
                "0000000000000000000000000000000000000000000000000000000000000001"
                "0000000000000000000000000000000000000000000000000000000000000002"
                "000000000000000000000000000000000000000000000000000000006553f100"
            )
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": req_id, "result": result})
        return httpx.Response(400, json={"error": "unknown"})

    respx.post(rpc_url).mock(side_effect=rpc_side_effect)
    rpc = RpcClient(rpc_url, max_retries=0)
    backfill_pool(rpc, pool, pipeline)
    result = verify_pool(rpc, pipeline.data_dir, pool.address)
    assert not result.ok
