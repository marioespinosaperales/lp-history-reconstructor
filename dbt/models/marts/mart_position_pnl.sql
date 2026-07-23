-- Per-position window metrics: fees % always; IL % only on clear exits.
with flows as (
    select * from {{ ref('int_token_cashflows') }}
    where value_token0 is not null
),

agg as (
    select
        token_id,
        any_value(pool_name) as pool_name,
        any_value(pool_address) as pool_address,
        any_value(wallet) as wallet,
        any_value(range_width_ticks) as range_width_ticks,
        any_value(range_bucket) as range_bucket,
        any_value(token0_symbol) as token0_symbol,
        sum(case when event_name = 'IncreaseLiquidity' then value_token0 else 0 end)
            as deposited_token0,
        sum(case when event_name = 'DecreaseLiquidity' then value_token0 else 0 end)
            as withdrawn_token0,
        sum(case when event_name = 'Collect' then value_token0 else 0 end)
            as collected_token0,
        sum(case when event_name = 'IncreaseLiquidity' then amount0_raw else 0 end)
            as deposited_amount0_raw,
        sum(case when event_name = 'IncreaseLiquidity' then amount1_raw else 0 end)
            as deposited_amount1_raw,
        min(block_number) as first_block,
        max(block_number) as last_block,
        count(*) as flow_events
    from flows
    group by token_id
),

exit_px as (
    select
        f.token_id,
        f.token0_per_token1,
        row_number() over (
            partition by f.token_id
            order by f.block_number desc, f.log_index desc
        ) as rn
    from flows f
),

marked as (
    select
        a.*,
        e.token0_per_token1 as exit_token0_per_token1,
        p.token0_decimals,
        p.token1_decimals,
        try_cast(p.liquidity as double) as on_chain_liquidity,
        coalesce(p.is_full_range, false) as is_full_range,
        p.range_width_pct as snapshot_range_width_pct,
        p.wallet_source,
        coalesce(a.wallet, p.wallet) as wallet_resolved
    from agg a
    left join exit_px e
        on a.token_id = e.token_id and e.rn = 1
    left join {{ ref('stg_nft_positions') }} p
        on a.token_id = p.token_id
),

scored as (
    select
        token_id,
        pool_name,
        pool_address,
        wallet_resolved as wallet,
        wallet_source,
        range_width_ticks,
        is_full_range,
        case
            when is_full_range then null
            when snapshot_range_width_pct is not null then snapshot_range_width_pct
            when range_width_ticks is null then null
            when range_width_ticks >= 1000000 then null
            else power(1.0001, range_width_ticks) - 1.0
        end as range_width_pct,
        case when is_full_range then 'full' else range_bucket end as range_bucket,
        token0_symbol,
        deposited_token0,
        withdrawn_token0,
        collected_token0,
        on_chain_liquidity,
        greatest(collected_token0 - withdrawn_token0, 0) as fees_proxy_token0,
        case
            when exit_token0_per_token1 is null or deposited_token0 = 0 then null
            else
                (deposited_amount0_raw / power(10.0, token0_decimals))
                + (deposited_amount1_raw / power(10.0, token1_decimals))
                * exit_token0_per_token1
        end as hodl_token0,
        -- Clear exit: liquidity gone on-chain, or ≥85% of deposit withdrawn in-window
        (
            deposited_token0 > 0
            and (
                coalesce(on_chain_liquidity, 0) = 0
                or withdrawn_token0 >= 0.85 * deposited_token0
            )
        ) as is_clear_exit,
        first_block,
        last_block,
        flow_events,
        case
            when deposited_token0 > 0 and collected_token0 > 0 then 'active_cycle'
            when collected_token0 > 0 then 'collect_only'
            when deposited_token0 > 0 then 'deposit_only'
            else 'other'
        end as cycle_kind
    from marked
)

select
    token_id,
    pool_name,
    pool_address,
    wallet,
    wallet_source,
    range_width_ticks,
    range_width_pct,
    is_full_range,
    range_bucket,
    token0_symbol,
    deposited_token0,
    withdrawn_token0,
    collected_token0,
    on_chain_liquidity,
    fees_proxy_token0,
    hodl_token0,
    is_clear_exit,
    -- IL ≈ principal returned vs HODL bag (fees excluded); only on clear exits
    case
        when is_clear_exit and hodl_token0 > 0
            then withdrawn_token0 - hodl_token0
        else null
    end as il_vs_hodl_token0,
    case
        when is_clear_exit and hodl_token0 > 0
            then (withdrawn_token0 - hodl_token0) / hodl_token0
        else null
    end as il_vs_hodl_pct,
    case
        when deposited_token0 > 0 and fees_proxy_token0 > 0
            then fees_proxy_token0 / deposited_token0
        else null
    end as fees_on_deposit_pct,
    -- Net after clear exit: principal IL + fees, as % of HODL
    case
        when is_clear_exit and hodl_token0 > 0
            then (withdrawn_token0 + fees_proxy_token0 - hodl_token0) / hodl_token0
        else null
    end as net_vs_hodl_pct,
    first_block,
    last_block,
    flow_events,
    cycle_kind
from scored
