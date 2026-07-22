"""JSON-RPC client for Ethereum (Alchemy HTTPS).

Thin wrapper over httpx with retries/backoff. Keeps web3 only for ABI decoding
elsewhere — RPC transport stays explicit and easy to mock in tests.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class RpcClient:
    def __init__(
        self,
        url: str,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 5,
        backoff_seconds: float = 1.5,
    ) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._id = 0

    def call(self, method: str, params: list[Any] | None = None) -> Any:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": method,
            "params": params or [],
        }
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                delay = self.backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "RPC retry %d/%d in %.1fs: %s", attempt, self.max_retries, delay, method
                )
                time.sleep(delay)
            try:
                response = httpx.post(
                    self.url, json=payload, timeout=self.timeout_seconds
                )
                if response.status_code in RETRYABLE_STATUS:
                    last_error = httpx.HTTPStatusError(
                        f"HTTP {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                    continue
                response.raise_for_status()
                body = response.json()
                if "error" in body and body["error"]:
                    raise RuntimeError(f"RPC error for {method}: {body['error']}")
                return body["result"]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in RETRYABLE_STATUS:
                    last_error = exc
                    continue
                raise RuntimeError(
                    f"RPC HTTP {exc.response.status_code} for {method}. "
                    "Public endpoints often block eth_getLogs — use Alchemy "
                    "(set LP_ETH_RPC_URL in .env)."
                ) from exc
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
                continue

        raise RuntimeError(f"RPC retries exhausted for {method}") from last_error

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber"), 16)

    def get_logs(
        self,
        *,
        address: str,
        topics: list[str | None] | None = None,
        from_block: int,
        to_block: int,
    ) -> list[dict[str, Any]]:
        filter_params: dict[str, Any] = {
            "address": address,
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
        }
        if topics is not None:
            filter_params["topics"] = topics
        return self.call("eth_getLogs", [filter_params])

    def eth_call(self, *, to: str, data: str, block: int | str = "latest") -> str:
        block_tag = hex(block) if isinstance(block, int) else block
        return self.call("eth_call", [{"to": to, "data": data}, block_tag])
