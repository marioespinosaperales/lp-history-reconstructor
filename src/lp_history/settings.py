"""Load and validate project configuration.

Declarative config lives in ``config/*.yaml``. Secrets enter ONLY via
environment variables (``LP_`` prefix), never via YAML.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


class PoolConfig(BaseModel):
    name: str
    address: str
    protocol: str = "uniswap_v2"
    enabled: bool = True
    fee_tier: int | None = None
    token0_symbol: str
    token1_symbol: str
    token0_decimals: int = Field(ge=0, le=18)
    token1_decimals: int = Field(ge=0, le=18)
    # Canonical mainnet addresses for filtering NPM positions to this pool
    token0_address: str | None = None
    token1_address: str | None = None


class NpmConfig(BaseModel):
    name: str = "uniswap_v3_npm"
    address: str = "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"
    enabled: bool = True


class PoolsFile(BaseModel):
    pools: list[PoolConfig] = Field(min_length=1)


class NpmFile(BaseModel):
    npm: NpmConfig


class PipelineConfig(BaseModel):
    data_dir: Path = Path("./data")
    checkpoint_dir: Path = Path("./data/checkpoints")
    chunk_size: int = Field(default=2000, ge=1, le=10_000)
    lookback_blocks: int = Field(default=50_000, ge=1)
    confirmations: int = Field(default=12, ge=0)
    rpc_timeout_seconds: float = 30.0
    rpc_max_retries: int = 5
    rpc_backoff_seconds: float = 1.5
    npm_verify_sample: int = Field(default=5, ge=1, le=50)

    def resolve(self, root: Path) -> PipelineConfig:
        return self.model_copy(
            update={
                "data_dir": (root / self.data_dir).resolve(),
                "checkpoint_dir": (root / self.checkpoint_dir).resolve(),
            }
        )


class Secrets(BaseSettings):
    """Secrets and env overrides. Example: LP_ETH_RPC_URL=https://..."""

    model_config = SettingsConfigDict(env_prefix="LP_", env_file=".env", extra="ignore")

    eth_rpc_url: str | None = None


class Settings(BaseModel):
    pools: list[PoolConfig]
    npm: NpmConfig
    pipeline: PipelineConfig
    secrets: Secrets


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_settings(config_dir: Path | None = None) -> Settings:
    config_dir = config_dir or CONFIG_DIR
    pools = PoolsFile.model_validate(_load_yaml(config_dir / "pools.yaml")).pools
    npm_raw = _load_yaml(config_dir / "npm.yaml")
    npm = NpmFile.model_validate(npm_raw).npm if npm_raw else NpmConfig(enabled=False)
    pipeline = PipelineConfig.model_validate(_load_yaml(config_dir / "pipelines.yaml"))
    return Settings(
        pools=pools,
        npm=npm,
        pipeline=pipeline.resolve(PROJECT_ROOT),
        secrets=Secrets(),
    )


def require_rpc_url(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    url = settings.secrets.eth_rpc_url
    if not url:
        raise RuntimeError(
            "LP_ETH_RPC_URL is not set. Copy .env.example to .env and add your Alchemy HTTPS URL."
        )
    # Validate shape without requiring network
    HttpUrl(url)
    return url
