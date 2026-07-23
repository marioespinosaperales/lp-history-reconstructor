-- Pool-level activity in the indexed window (context for the dashboard).
with events as (
    select * from {{ ref('stg_pool_events') }}
),

swaps as (
    select
        pool_address,
        count(*) as swap_count,
        min(block_number) as first_block,
        max(block_number) as last_block
    from events
    where event_name = 'Swap'
    group by pool_address
),

mints as (
    select
        pool_address,
        count(*) as mint_count
    from events
    where event_name = 'Mint'
    group by pool_address
),

burns as (
    select
        pool_address,
        count(*) as burn_count
    from events
    where event_name = 'Burn'
    group by pool_address
),

positions as (
    select
        pool_address,
        any_value(pool_name) as pool_name,
        any_value(token0_symbol) as token0_symbol,
        any_value(token1_symbol) as token1_symbol,
        count(*) as nft_positions_matched
    from {{ ref('stg_nft_positions') }}
    group by pool_address
)

select
    p.pool_name,
    p.pool_address,
    p.token0_symbol,
    p.token1_symbol,
    p.nft_positions_matched,
    coalesce(s.swap_count, 0) as swap_count,
    coalesce(m.mint_count, 0) as mint_count,
    coalesce(b.burn_count, 0) as burn_count,
    s.first_block,
    s.last_block
from positions p
left join swaps s on p.pool_address = s.pool_address
left join mints m on p.pool_address = m.pool_address
left join burns b on p.pool_address = b.pool_address
