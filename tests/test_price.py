import math

from lp_history.analytics.price import (
    is_full_range,
    range_bucket,
    range_width_pct,
    raw_price_t1_per_t0,
    token0_per_token1,
    value_in_token0,
)
from lp_history.index.npm_abi import decode_owner_of, owner_of_calldata


def test_raw_price_unity_sqrt():
    assert math.isclose(raw_price_t1_per_t0(2**96), 1.0, rel_tol=1e-12)


def test_usdc_weth_value_at_parity_raw():
    sqrt = 2**96
    usdc_per_weth = token0_per_token1(sqrt, decimals0=6, decimals1=18)
    assert math.isclose(usdc_per_weth, 1e12, rel_tol=1e-9)
    assert math.isclose(
        value_in_token0(1_000_000, 0, sqrt, decimals0=6, decimals1=18),
        1.0,
        rel_tol=1e-9,
    )


def test_range_buckets_and_full_range():
    assert range_bucket(150) == "narrow"
    assert range_bucket(2010) == "mid"
    assert range_bucket(5000) == "wide"
    assert range_bucket(1_774_540) == "full"
    assert is_full_range(1_774_540)
    assert range_width_pct(1_774_540) is None
    assert range_width_pct(200) is not None
    assert math.isclose(range_width_pct(200), 1.0001**200 - 1.0, rel_tol=1e-12)


def test_owner_of_calldata_and_decode():
    data = owner_of_calldata(123)
    assert data.startswith("0x")
    # address 0xaAa... padded in ABI word
    encoded = (
        "0x"
        + "000000000000000000000000aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    assert decode_owner_of(encoded) == "0xaAaAaAaaAaAaAaaAaAAAAAAAAaaaAaAaAaaAaaAa"
