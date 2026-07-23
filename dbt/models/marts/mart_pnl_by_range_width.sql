select
    pool_name,
    pool_address,
    range_bucket,
    count(*) as positions,
    count(distinct wallet) as wallets,
    avg(range_width_ticks) as avg_range_width_ticks,
    sum(deposited_token0) as deposited_token0,
    sum(collected_token0) as collected_token0,
    sum(fees_proxy_token0) as fees_proxy_token0,
    sum(hodl_token0) as hodl_token0,
    sum(pnl_vs_hodl_token0) as pnl_vs_hodl_token0,
    avg(pnl_vs_hodl_token0) as avg_pnl_vs_hodl_token0,
    sum(case when pnl_vs_hodl_token0 > 0 then 1 else 0 end) as positions_beat_hodl,
    any_value(token0_symbol) as token0_symbol
from {{ ref('mart_position_pnl') }}
group by pool_name, pool_address, range_bucket
order by
    case range_bucket
        when 'narrow' then 1
        when 'mid' then 2
        else 3
    end
