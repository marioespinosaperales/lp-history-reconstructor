"""Uniswap V3 price helpers (token0-denominated value).

``sqrt_price_x96`` encodes raw ``token1/token0``. Human USDC-per-WETH for the
default USDC/WETH pool is derived from decimals, not hardcoded elsewhere.
"""

from __future__ import annotations

Q96 = 2**96


def raw_price_t1_per_t0(sqrt_price_x96: int | float) -> float:
    """Raw token1 per token0 from sqrtPriceX96."""
    ratio = float(sqrt_price_x96) / Q96
    return ratio * ratio


def token0_per_token1(sqrt_price_x96: int | float, *, decimals0: int, decimals1: int) -> float:
    """Human token0 per 1 human token1 (e.g. USDC per WETH)."""
    raw = raw_price_t1_per_t0(sqrt_price_x96)
    if raw <= 0:
        return 0.0
    # human_t1_per_t0 = raw * 10**(decimals0 - decimals1)
    # invert → human_t0_per_t1
    return (10 ** (decimals1 - decimals0)) / raw


def value_in_token0(
    amount0_raw: int | float,
    amount1_raw: int | float,
    sqrt_price_x96: int | float,
    *,
    decimals0: int,
    decimals1: int,
) -> float:
    """Value a (amount0, amount1) bag in human token0 units."""
    a0 = float(amount0_raw) / (10**decimals0)
    a1 = float(amount1_raw) / (10**decimals1)
    px = token0_per_token1(sqrt_price_x96, decimals0=decimals0, decimals1=decimals1)
    return a0 + a1 * px


def range_bucket(width_ticks: int) -> str:
    """Coarse bucket for narrow-vs-wide LP storytelling."""
    if width_ticks < 500:
        return "narrow"
    if width_ticks < 3000:
        return "mid"
    return "wide"
