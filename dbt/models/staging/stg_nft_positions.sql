with src as (
    select * from {{ source('raw', 'nft_positions') }}
)

select
    cast(pool_name as varchar) as pool_name,
    lower(cast(pool_address as varchar)) as pool_address,
    lower(cast(npm_address as varchar)) as npm_address,
    cast(token_id as bigint) as token_id,
    cast(wallet as varchar) as wallet,
    cast(tick_lower as integer) as tick_lower,
    cast(tick_upper as integer) as tick_upper,
    cast(range_width_ticks as integer) as range_width_ticks,
    cast(range_bucket as varchar) as range_bucket,
    cast(fee_tier as integer) as fee_tier,
    cast(liquidity as varchar) as liquidity,
    cast(token0 as varchar) as token0,
    cast(token1 as varchar) as token1,
    cast(token0_decimals as integer) as token0_decimals,
    cast(token1_decimals as integer) as token1_decimals,
    cast(token0_symbol as varchar) as token0_symbol,
    cast(token1_symbol as varchar) as token1_symbol
from src
where token_id is not null
