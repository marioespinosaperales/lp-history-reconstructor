---
title: LP PnL by Range Width
---

Uniswap V3 USDC/WETH (0.05%): NPM wallets → **fees %** and **IL % on clear exits**.

- Prefer **% returns** (fees/deposit) over absolute USDC.
- `range_width_ticks` are Uniswap ticks. Width % = `1.0001^ticks − 1` (null for **full-range** ≈ V2-style).
- **IL vs HODL** only when the position clearly exited in-window (on-chain L=0 or ≥85% withdrawn). Open positions no longer show fake −99% “losses”.
- Wallets missing from Transfer history are filled via `ownerOf(tokenId)`.

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
    full_range_positions,
    fees_proxy_token0,
    median_fees_on_deposit_pct,
    median_il_vs_hodl_pct,
    median_net_vs_hodl_pct,
    clear_exits
from lp.pnl_by_range_width
order by
    case range_bucket
        when 'narrow' then 1
        when 'mid' then 2
        when 'wide' then 3
        else 4
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
  <Column id=median_il_vs_hodl_pct title="Median IL vs HODL" fmt=pct2 />
  <Column id=median_net_vs_hodl_pct title="Median net vs HODL" fmt=pct2 />
  <Column id=clear_exits title="Clear exits" />
</DataTable>

## Positions

Sorted by fees/deposit %. IL columns populate only on clear exits.

```sql positions
select
    token_id,
    wallet,
    wallet_source,
    range_width_ticks,
    range_width_pct,
    range_bucket,
    is_full_range,
    deposited_token0,
    fees_proxy_token0,
    fees_on_deposit_pct,
    is_clear_exit,
    il_vs_hodl_pct,
    net_vs_hodl_pct,
    cycle_kind
from lp.position_pnl
order by fees_on_deposit_pct desc nulls last, fees_proxy_token0 desc
limit 50
```

<DataTable data={positions}>
  <Column id=token_id />
  <Column id=wallet />
  <Column id=wallet_source title="Wallet src" />
  <Column id=range_width_ticks title="Ticks" />
  <Column id=range_width_pct title="Width %" fmt=pct1 />
  <Column id=range_bucket title="Bucket" />
  <Column id=deposited_token0 title="Deposited $" fmt=num2 />
  <Column id=fees_proxy_token0 title="Fees $" fmt=num2 />
  <Column id=fees_on_deposit_pct title="Fees / deposit" fmt=pct2 />
  <Column id=il_vs_hodl_pct title="IL vs HODL" fmt=pct2 />
  <Column id=net_vs_hodl_pct title="Net vs HODL" fmt=pct2 />
  <Column id=cycle_kind title="Cycle" />
</DataTable>
