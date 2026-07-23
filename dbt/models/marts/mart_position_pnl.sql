-- Per-position window PnL vs HODL (token0 units). Short lookbacks are approximate.
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

-- Exit mark: last priced flow for the token (Collect/Decrease preferred via last_block)
exit_px as (
    select
        f.token_id,
        f.token0_per_token1,
        f.token0_symbol,
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
        p.token1_decimals
    from agg a
    left join exit_px e
        on a.token_id = e.token_id and e.rn = 1
    left join {{ ref('stg_nft_positions') }} p
        on a.token_id = p.token_id
)

select
    token_id,
    pool_name,
    pool_address,
    wallet,
    range_width_ticks,
    range_bucket,
    token0_symbol,
    deposited_token0,
    withdrawn_token0,
    collected_token0,
    -- Collect includes principal after Decrease + fees; fees_proxy ≈ collect - decrease
    greatest(collected_token0 - withdrawn_token0, 0) as fees_proxy_token0,
    -- HODL: still hold deposited raw bags marked at exit price
    case
        when exit_token0_per_token1 is null or deposited_token0 = 0 then null
        else
            (deposited_amount0_raw / power(10.0, token0_decimals))
            + (deposited_amount1_raw / power(10.0, token1_decimals)) * exit_token0_per_token1
    end as hodl_token0,
    -- Only meaningful when the window saw both deposits and Collect proceeds
    case
        when exit_token0_per_token1 is null
            or deposited_token0 = 0
            or collected_token0 = 0 then null
        else
            collected_token0
            - (
                (deposited_amount0_raw / power(10.0, token0_decimals))
                + (deposited_amount1_raw / power(10.0, token1_decimals)) * exit_token0_per_token1
            )
    end as pnl_vs_hodl_token0,
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
