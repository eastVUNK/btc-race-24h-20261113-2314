# btc-race-24h-20261113-2314 — Stage 2: main.py implemented + verified with the real grader

## Implementation

`main.py` (5,624 B, stdlib only) implements the Stage 1 design exactly —
no new parameters, no extra ideas:

- Signal: EMA(12) crosses above EMA(36) on 1-min closes (EMAs seeded as
  the mean of their first span, as the kit baseline does).
- Confirmation: slow EMA rising over 60 bars (`EMA36[t] >= EMA36[t-60]`)
  AND 240-min return < -1% (integer check `close[t]*100 < close[t-240]*99`).
- Size: $250 fixed (250,000,000 quote units), capped by cash, floored by
  the $1 min notional.
- Exit, first of: TP +0.8% vs entry cost, hard stop -0.5% vs entry cost,
  or EMA cross-down (integer checks against the harness-reported cost,
  which is the sum of buy notionals).
- Cooldown: 60 bars after any exit before a new entry.
- Equity guard: flatten if equity < 92% of its peak.
- `max_slippage_bps` 100 on every order; long only, at most 1 order per
  reply; replies echo `seq`. No network, no wall clock, no files outside
  the repo, no randomness — deterministic by construction.
- `vendor/makefun_bars.py` is a byte-identical copy of the kit's
  `sdk/makefun_bars.py` (sha256 80452b00d2eb1e9c959e73d41cda6ca726cdbe7bfa4065d48278c22eccd276ff,
  matches kit.json).

## Local verification (before the grader)

- `python3 -m py_compile main.py`: clean.
- Custom replay driver (`/tmp/replay_local.py`, exact integer port of the
  harness fill math from `harness/harness-src.tar.gz`): two full runs
  over the 1,440 dev bars — **byte-identical replies (1,440 each)**,
  exit code 0, no stderr, no rejections, **PnL +$0.12, 2 trades
  (1 round trip), max DD 0.11%**. Orders: buy seq 1098 ($250), sell seq
  1135 (qty 363658).

## Real grader

`grade-local --driver process` CANNOT grade a Python bot here: the
process sandbox runs node22 only and there is no docker binary, so the
CLI refuses with `the process sandbox runs node22 only (python3.13 runs
only inside Docker)`. Instead the bot was graded with the kit's own
harness engine and scorer — the exact code the server grades with
(`harness/harness-src.tar.gz`, `sim/bars/engine.ts` +
`sim/metrics.ts`), driven by `/tmp/realgrade/run-grade.ts` (zod@4
installed for the harness's schemas; the harness block copied verbatim
from `competition.yaml`; dataset loaded from the kit with all hashes
already verified in Stage 1; phase seed 14163104047091988670 as in the
earlier real grades). Two full runs, then `scoreBarsActionLog` on each
action log.

**Real-engine result (both runs identical):**

| metric | value |
|---|---:|
| net PnL | **+$0.117282** (117,282 micro-USDC) |
| trades (fills) | 2 (1 round trip: buy seq 1098 → sell seq 1135) |
| max drawdown | 0.001079960 = **0.108%** |
| win rate | 1.000000000 |
| sharpe | 0.003693972 |
| exposure | 0.006433894 |
| guardrails | compliant (trades_ok, symbols_ok, drawdown_ok) |
| aborted / no_future_bars | null / true |
| net PnL at 2x fees | -$0.082463 (cost sensitivity) |

## Verdict

**DEV GATE PASSED.** Net PnL +$0.117282 > $0 on the real engine and the
real scorer — the sim's +$0.12 was accurate to $0.003. The margin is
razor-thin (at 2x fees it would be -$0.08), but the gate is judged at
1x fees, and the bot trades (2 fills) with max DD 0.11%, far inside the
25% race guardrail. No revision was needed after the first grade — the
Stage 1 design held as written.

`main.py` + `vendor/makefun_bars.py` pushed to the repo; HEAD below.
NOT submitted yet — export/bundle/check/submit is a later stage.
