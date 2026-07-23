select
    pool_name,
    pool_address,
    range_bucket,
    count(*) as positions,
    count(distinct wallet) as wallets,
    avg(range_width_ticks) as avg_range_width_ticks,
    avg(range_width_pct) as avg_range_width_pct,
    sum(case when is_full_range then 1 else 0 end) as full_range_positions,
    sum(deposited_token0) as deposited_token0,
    sum(collected_token0) as collected_token0,
    sum(fees_proxy_token0) as fees_proxy_token0,
    sum(hodl_token0) as hodl_token0,
    avg(fees_on_deposit_pct) as avg_fees_on_deposit_pct,
    median(fees_on_deposit_pct) as median_fees_on_deposit_pct,
    avg(il_vs_hodl_pct) as avg_il_vs_hodl_pct,
    median(il_vs_hodl_pct) as median_il_vs_hodl_pct,
    avg(net_vs_hodl_pct) as avg_net_vs_hodl_pct,
    median(net_vs_hodl_pct) as median_net_vs_hodl_pct,
    sum(case when is_clear_exit then 1 else 0 end) as clear_exits,
    sum(case when il_vs_hodl_pct > 0 then 1 else 0 end) as positions_beat_hodl_on_il,
    any_value(token0_symbol) as token0_symbol
from {{ ref('mart_position_pnl') }}
group by pool_name, pool_address, range_bucket
order by
    case range_bucket
        when 'narrow' then 1
        when 'mid' then 2
        when 'wide' then 3
        else 4
    end
