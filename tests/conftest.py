import json
from pathlib import Path

import pytest

from lp_history.settings import PipelineConfig, PoolConfig

FIXTURES = Path(__file__).parent / "fixtures"

POOL = "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc"


@pytest.fixture
def sync_logs() -> list[dict]:
    return json.loads((FIXTURES / "sync_logs.json").read_text(encoding="utf-8"))


@pytest.fixture
def v3_mint_logs() -> list[dict]:
    return json.loads((FIXTURES / "v3_mint_logs.json").read_text(encoding="utf-8"))


@pytest.fixture
def pool() -> PoolConfig:
    return PoolConfig(
        name="weth_usdc",
        address=POOL,
        protocol="uniswap_v2",
        token0_symbol="USDC",
        token1_symbol="WETH",
        token0_decimals=6,
        token1_decimals=18,
    )


@pytest.fixture
def pipeline(tmp_path: Path) -> PipelineConfig:
    return PipelineConfig(
        data_dir=tmp_path / "data",
        checkpoint_dir=tmp_path / "checkpoints",
        chunk_size=100,
        lookback_blocks=500,
        confirmations=0,
        rpc_max_retries=0,
    )
