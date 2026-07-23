with src as (
    select * from {{ source('raw', 'npm_events') }}
)

select
    lower(cast(contract_address as varchar)) as npm_address,
    cast(protocol as varchar) as protocol,
    cast(event_name as varchar) as event_name,
    cast(block_number as bigint) as block_number,
    cast(log_index as bigint) as log_index,
    cast(tx_hash as varchar) as tx_hash,
    try_cast(token_id as bigint) as token_id,
    cast(from_address as varchar) as from_address,
    cast(to_address as varchar) as to_address,
    cast(liquidity as varchar) as liquidity,
    cast(amount0 as varchar) as amount0,
    cast(amount1 as varchar) as amount1,
    cast(recipient as varchar) as recipient
from src
where try_cast(token_id as bigint) is not null
