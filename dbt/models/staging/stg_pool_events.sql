with src as (
    select * from {{ source('raw', 'pool_events') }}
)

select
    lower(cast(pool_address as varchar)) as pool_address,
    cast(protocol as varchar) as protocol,
    cast(event_name as varchar) as event_name,
    cast(block_number as bigint) as block_number,
    cast(log_index as bigint) as log_index,
    cast(tx_hash as varchar) as tx_hash,
    cast(amount0 as varchar) as amount0,
    cast(amount1 as varchar) as amount1,
    cast(liquidity as varchar) as liquidity,
    cast(sqrt_price_x96 as varchar) as sqrt_price_x96,
    try_cast(tick as integer) as tick,
    cast(owner as varchar) as owner,
    try_cast(tick_lower as integer) as tick_lower,
    try_cast(tick_upper as integer) as tick_upper,
    cast(sender as varchar) as sender,
    cast(recipient as varchar) as recipient,
    cast(to_address as varchar) as to_address
from src
