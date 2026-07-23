---
title: LP PnL by Range Width
---

Uniswap V3 USDC/WETH (0.05%): NPM wallet attribution → fees + IL vs HODL by range width.
Built from on-chain events (Alchemy) → Parquet → DuckDB → dbt. Short lookbacks are directional.

Source: [lp-history-reconstructor](https://github.com/marioespinosaperales/lp-history-reconstructor).

```sql pool
select *
from lp.pool_activity
limit 1
```

<BigValue data={pool} value=nft_positions_matched title="Pool-matched NFTs" />
<BigValue data={pool} value=swap_count title="Swaps in window" />
<BigValue data={pool} value=mint_count title="Mints in window" />

## Narrow vs wide: PnL vs HODL

Values in token0 (USDC). `fees_proxy ≈ Collect − Decrease`. `pnl_vs_hodl` compares Collect proceeds to holding the deposited bag at exit price.

```sql by_range
select
    range_bucket,
    positions,
    wallets,
    avg_range_width_ticks,
    deposited_token0,
    fees_proxy_token0,
    hodl_token0,
    pnl_vs_hodl_token0,
    avg_pnl_vs_hodl_token0,
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
  y=pnl_vs_hodl_token0
  title="Total PnL vs HODL by range bucket (token0)"
/>

<DataTable data={by_range}>
  <Column id=range_bucket title="Range" />
  <Column id=positions />
  <Column id=wallets />
  <Column id=avg_range_width_ticks title="Avg width (ticks)" fmt=num0 />
  <Column id=fees_proxy_token0 title="Fees proxy" fmt=num2 />
  <Column id=pnl_vs_hodl_token0 title="PnL vs HODL" fmt=num2 />
  <Column id=avg_pnl_vs_hodl_token0 title="Avg PnL vs HODL" fmt=num2 />
  <Column id=positions_beat_hodl title="Beat HODL" />
</DataTable>

## Positions (sample)

```sql positions
select
    token_id,
    wallet,
    range_width_ticks,
    range_bucket,
    deposited_token0,
    collected_token0,
    fees_proxy_token0,
    hodl_token0,
    pnl_vs_hodl_token0,
    cycle_kind
from lp.position_pnl
order by range_width_ticks
limit 50
```

<DataTable data={positions}>
  <Column id=token_id />
  <Column id=wallet />
  <Column id=range_width_ticks title="Width" />
  <Column id=range_bucket title="Bucket" />
  <Column id=deposited_token0 title="Deposited" fmt=num2 />
  <Column id=fees_proxy_token0 title="Fees proxy" fmt=num2 />
  <Column id=pnl_vs_hodl_token0 title="PnL vs HODL" fmt=num2 />
  <Column id=cycle_kind title="Cycle" />
</DataTable>
