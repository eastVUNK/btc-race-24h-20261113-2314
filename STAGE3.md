# btc-race-24h-20261113-2314 — Stage 3: genuine revision (equity-guard latch)

## The revision (main.py, the only code change)

**Problem found on re-inspection:** the 8% equity guard only flattened the
current position. After the 60-bar cooldown the bot could re-enter the
same crashing market and bleed again — and on the live race window a
guard that only fires once is not really a hard stop.

**Fix — guard latch (real code-path change, not a comment/format edit):**

- `GUARD_TRIPPED` module flag, set the first time equity falls below
  92% of its peak.
- The guard is now evaluated **every batch**, not only while holding:
  equity can fall below the guard level while flat too (a slow bleed
  across losing round trips), and the old code would never have noticed.
- Once latched, the flat branch returns `[]` before any entry check —
  no new buys for the rest of the run. Exits are untouched: a held
  position is still flattened by the guard/stop/TP/cross-down logic.

No strategy change, no parameter change: same FAST=12 / SLOW=36,
slope60 ≥ 0, washout ret240 < -1%, $250 size, TP +0.8% / stop -0.5%,
cooldown 60, guard 8%.

## Proof the latch works (synthetic crash test, /tmp/test_latch.py)

A hand-built series through the bot's real stdin/stdout protocol:
decline 70k→67k, flat, rise to 68k (cross #1 ignored), shallow dip to
67.8k, slow grind — qualifying entry at bar 310 — then a one-bar gap
crash to $40k (equity ~$897 < 92% of the $1,000 peak), recovery, and a
second identical setup with a qualifying cross at bar ~776.

| | Stage 2 (no latch) | Stage 3 (latch) |
|---|---|---|
| orders | buy 310, sell 315, **buy 776, sell 777** | buy 310, sell 315 |
| buys after the crash | 1 (re-entry, instantly guard-sold again) | **0** |
| final cash | $897.80 | $897.98 |

The Stage 2 re-entry was a pure fee burn: it bought at 776 and the
guard sold it one bar later. The latch removes exactly that.

## Re-verification (dev window, unchanged by design)

- `py_compile`: clean.
- Local replay driver (`/tmp/replay_local.py`, exact integer port of the
  harness fill math): two full runs, **byte-identical replies**,
  PnL **+$0.12**, 2 trades, max DD 0.11%, same orders (buy seq 1098,
  sell seq 1135). The guard never trips on dev (max DD 0.11% << 8%),
  so the latch is inert there — as intended.
- Real engine re-grade (`/tmp/realgrade/run-grade.ts`, kit's own
  `sim/bars/engine.ts` + `sim/metrics.ts`): both runs identical,
  no abort, no_future_bars true.
  **Net PnL +$0.117282 (117,282 micro-USDC)** — byte-for-byte the same
  as Stage 2. Max drawdown 0.001079960 (0.108%), win rate 1.0,
  guardrails compliant, 2 fills, cost sensitivity at 2x fees -$0.082463.

## Verdict

**DEV GATE STILL PASSED.** The revision changes nothing on the dev
window and removes a real failure mode on the live race window. No
revert needed.

Revised `main.py` pushed; HEAD below. NOT submitted yet — Stage 4 is
the final review, then export/bundle/check/submit from the main chat.

## Note on tooling

`/tmp` was partially wiped between Stage 2 and Stage 3
(`replay_local.py`, `realgrade/`, `harness-src/` gone). Everything was
rebuilt from the kit tarball (persistent) and re-verified from scratch.
Test scripts kept at `~/workspace/makefun/btc-race-stage3-tests/`
(`test_latch.py`, `replay_local.py`, `run-grade.ts`) so a wipe cannot
block Stage 4.
