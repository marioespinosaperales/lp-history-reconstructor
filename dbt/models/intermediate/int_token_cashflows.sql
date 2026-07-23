-- NPM cashflows for pool-matched NFTs, valued in human token0 (e.g. USDC).
with positions as (
    select * from {{ ref('stg_nft_positions') }}
),

flows as (
    select
        e.token_id,
        e.event_name,
        e.block_number,
        e.log_index,
        e.tx_hash,
        try_cast(e.amount0 as double) as amount0_raw,
        try_cast(e.amount1 as double) as amount1_raw,
        p.pool_name,
        p.pool_address,
        p.wallet,
        p.range_width_ticks,
        p.range_bucket,
        p.token0_decimals,
        p.token1_decimals,
        p.token0_symbol,
        p.token1_symbol
    from {{ ref('stg_npm_events') }} e
    inner join positions p on e.token_id = p.token_id
    where e.event_name in ('IncreaseLiquidity', 'DecreaseLiquidity', 'Collect')
      and try_cast(e.amount0 as double) is not null
),

priced as (
    select
        f.*,
        bp.sqrt_price_x96,
        -- human token0 per human token1
        case
            when bp.sqrt_price_x96 is null or bp.sqrt_price_x96 <= 0 then null
            else
                power(10.0, f.token1_decimals - f.token0_decimals)
                / power(bp.sqrt_price_x96 / power(2.0, 96), 2)
        end as token0_per_token1
    from flows f
    asof left join {{ ref('int_block_prices') }} bp
        on f.pool_address = bp.pool_address
       and f.block_number >= bp.block_number
)

select
    token_id,
    event_name,
    block_number,
    log_index,
    tx_hash,
    pool_name,
    pool_address,
    wallet,
    range_width_ticks,
    range_bucket,
    token0_symbol,
    token1_symbol,
    amount0_raw,
    amount1_raw,
    sqrt_price_x96,
    token0_per_token1,
    case
        when token0_per_token1 is null then null
        else
            (amount0_raw / power(10.0, token0_decimals))
            + (amount1_raw / power(10.0, token1_decimals)) * token0_per_token1
    end as value_token0
from priced
