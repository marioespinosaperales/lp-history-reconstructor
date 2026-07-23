import math

from lp_history.analytics.price import (
    range_bucket,
    raw_price_t1_per_t0,
    token0_per_token1,
    value_in_token0,
)


def test_raw_price_unity_sqrt():
    # sqrtPriceX96 = 2^96 → raw price = 1
    assert math.isclose(raw_price_t1_per_t0(2**96), 1.0, rel_tol=1e-12)


def test_usdc_weth_value_at_parity_raw():
    # raw token1/token0 = 1 with 6/18 decimals → 1 WETH = 1e12 USDC (toy price)
    sqrt = 2**96
    usdc_per_weth = token0_per_token1(sqrt, decimals0=6, decimals1=18)
    assert math.isclose(usdc_per_weth, 1e12, rel_tol=1e-9)
    # 1e6 raw USDC (=1 USDC) + 0 WETH
    assert math.isclose(
        value_in_token0(1_000_000, 0, sqrt, decimals0=6, decimals1=18),
        1.0,
        rel_tol=1e-9,
    )


def test_range_buckets():
    assert range_bucket(150) == "narrow"
    assert range_bucket(2010) == "mid"
    assert range_bucket(5000) == "wide"
