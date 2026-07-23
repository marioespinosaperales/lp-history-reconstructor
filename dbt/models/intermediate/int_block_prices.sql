-- Last Swap sqrtPriceX96 per pool/block (price path for cashflow valuation).
with swaps as (
    select
        pool_address,
        block_number,
        log_index,
        try_cast(sqrt_price_x96 as double) as sqrt_price_x96,
        tick
    from {{ ref('stg_pool_events') }}
    where event_name = 'Swap'
      and sqrt_price_x96 is not null
      and try_cast(sqrt_price_x96 as double) > 0
),

ranked as (
    select
        *,
        row_number() over (
            partition by pool_address, block_number
            order by log_index desc
        ) as rn
    from swaps
)

select
    pool_address,
    block_number,
    sqrt_price_x96,
    tick
from ranked
where rn = 1
