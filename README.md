# btc-race-24h-20261113-2314

A BTC trading bot for make.fun's "Race a BTC trading bot live for 24 hours"
competition. It trades Coinbase Wrapped BTC (cbBTC) against USDC on 1-minute
on-chain bars from the Orca Whirlpool, starting from $1,000 paper USDC.

Strategy (see `STAGE1.md` for the full design): selective EMA trend —
EMA(12) crossing above EMA(36), confirmed by a rising slow EMA over 60 bars
and a 4-hour washout (240-min return below -1%), with quarter-size entries,
a +0.8% take-profit, a -0.5% hard stop, a cross-down exit, and a 60-bar
re-entry cooldown. Long only, no leverage, deterministic, standard library
only (`main.py`, Python 3.13).

- Competition: https://make.fun/bounty/btc-race-24h-20261113-2314
- Entry: `main.py` at the repository root (Stage 2).
- License: MIT.
