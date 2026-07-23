---
title: LP PnL by Range Width
---

Uniswap V3 USDC/WETH (0.05%): NPM wallets → fees + IL vs HODL by range width.
**Prefer % returns** (fees / deposit, PnL / HODL) over absolute USDC — a $1k position
up 5% beats a $1M position up $50k on strategy quality.

`range_width_ticks` are Uniswap ticks (`price = 1.0001^tick`). A width of **2040 ticks ≈ 22.6%**
price span (`1.0001^2040 − 1`), not 2.04%.

`fees_proxy ≈ Collect − Decrease` when both exist. **collect_only** rows often have no Decrease
in-window, so the Collect may mix **fees + principal** already owed — not pure rewards. Deposit
is null when the Increase sat outside the lookback.

Source: [lp-history-reconstructor](https://github.com/marioespinosaperales/lp-history-reconstructor).

```sql pool
select *
from lp.pool_activity
limit 1
```

<BigValue data={pool} value=nft_positions_matched title="Pool-matched NFTs" />
<BigValue data={pool} value=swap_count title="Swaps in window" />
<BigValue data={pool} value=mint_count title="Mints in window" />

## Narrow vs wide (relative returns)

```sql by_range
select
    range_bucket,
    positions,
    wallets,
    avg_range_width_ticks,
    avg_range_width_pct,
    deposited_token0,
    fees_proxy_token0,
    avg_fees_on_deposit_pct,
    median_fees_on_deposit_pct,
    avg_pnl_vs_hodl_pct,
    median_pnl_vs_hodl_pct,
    positions_beat_hodl
from lp.pnl_by_range_width
order by
    case range_bucket
        when 'narrow' then 1
        when 'mid' then 2
        else 3
    end
```

<BarChart
  data={by_range}
  x=range_bucket
  y=median_fees_on_deposit_pct
  title="Median fees / deposit by range bucket"
  yFmt=pct1
/>

<DataTable data={by_range}>
  <Column id=range_bucket title="Range" />
  <Column id=positions />
  <Column id=wallets />
  <Column id=avg_range_width_ticks title="Avg ticks" fmt=num0 />
  <Column id=avg_range_width_pct title="Avg width %" fmt=pct1 />
  <Column id=fees_proxy_token0 title="Fees proxy $" fmt=num2 />
  <Column id=median_fees_on_deposit_pct title="Median fees/deposit" fmt=pct2 />
  <Column id=median_pnl_vs_hodl_pct title="Median PnL vs HODL %" fmt=pct2 />
  <Column id=positions_beat_hodl title="Beat HODL" />
</DataTable>

## Positions

Sorted by fees/deposit % (strategy quality) when available.

```sql positions
select
    token_id,
    wallet,
    range_width_ticks,
    range_width_pct,
    range_bucket,
    deposited_token0,
    collected_token0,
    fees_proxy_token0,
    fees_on_deposit_pct,
    pnl_vs_hodl_token0,
    pnl_vs_hodl_pct,
    cycle_kind,
    on_chain_liquidity
from lp.position_pnl
order by fees_on_deposit_pct desc nulls last, fees_proxy_token0 desc
limit 50
```

<DataTable data={positions}>
  <Column id=token_id />
  <Column id=wallet />
  <Column id=range_width_ticks title="Ticks" />
  <Column id=range_width_pct title="Width %" fmt=pct1 />
  <Column id=range_bucket title="Bucket" />
  <Column id=deposited_token0 title="Deposited $" fmt=num2 />
  <Column id=fees_proxy_token0 title="Fees proxy $" fmt=num2 />
  <Column id=fees_on_deposit_pct title="Fees / deposit" fmt=pct2 />
  <Column id=pnl_vs_hodl_pct title="PnL vs HODL %" fmt=pct2 />
  <Column id=cycle_kind title="Cycle" />
</DataTable>
