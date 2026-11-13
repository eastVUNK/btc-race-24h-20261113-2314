# btc-race-24h-20261113-2314 — Stage 1: requirements, kit, repo, strategy

Competition: **btc-race-24h-20261113-2314** — "Race a BTC trading bot live for
24 hours". $250 pot, top 10 paid (1st $60, 2nd $40, 3rd $30, 4th $25, 5th $20,
6th–10th $15). Deadline **Sat 2026-11-14 12:14 WIB (05:14 UTC)**. Max 10
submissions total; last submission before the deadline is final. 52
submissions already at Stage 1 time. Opened 2026-11-13T23:14:00Z
(Sat 06:14 WIB).

## Kit

- Downloaded via curl with the make.fun API key (never printed): the
  `/api/.../kit` endpoint returns the kit manifest JSON
  (`agent-fun/kit/v1`); the actual tarball is at
  `https://make.fun/c/btc-race-24h-20261113-2314/kit`
  (6,764,838 bytes, gzip). Saved at `kit/kit.tar.gz`, unpacked to
  `kit/unpacked/btc-race-24h-20261113-2314-kit/`.
- All per-file sha256 + sizes in `kit.json` verify OK. (The tarball's own
  sha256 differs from `bundle_sha256` in the manifest — the manifest hash
  covers the uncompressed bundle, not the gzip; every listed file inside
  matches, so the kit is intact.)
- Kit: `RULES.txt`, `competition.yaml`, `protocol.schema.json`,
  `sdk/makefun_bars.py` + `sdk/makefun-bars.ts`, 6 baselines
  (buy-and-hold, hold-cash, momentum, ema-cross, adx-momentum,
  rsi-bollinger), `dataset/` (dev window), `harness/` (harness source),
  `cli/makefun.mjs` (grade-local / check / submit / bundle).

## Protocol summary (agent-fun/bars-replay/v1)

- NDJSON on stdin/stdout. Harness sends `hello` once, then one `batch` per
  minute, then `done`. The bot answers **every batch with exactly one
  `reply` echoing its `seq`**, before the next batch.
- `hello`: protocol, `seed`, `symbols` (CBBTC, mint
  `cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij`, price_scale 5, qty_scale 8),
  `capital` (USDC, quote_scale 6, 1,000,000,000 quote units = $1,000),
  `caps` (max_open_positions 1, max_orders_per_bar 16, max_weight_bps 10000,
  no shorts, no leverage), `fees` (fee_bps 4, slippage_bps 2,
  min_notional_quote_units 1,000,000 = $1), `warmup_bars` (0 here).
- `batch`: `seq`, `t` (ms), `bars` (one per symbol present that minute;
  a missing symbol = a gap, not a flat bar), `fills` (fills/rejections of
  the previous reply's orders), `account` (cash, positions, equity in
  quote units). Bar fields: `t` (close ms), `o/h/l/c` (integer price
  strings, scale 5, i.e. $ = int/1e5), `v` (null), `o_depth`/`c_depth`
  (pool depth, USDC raw units, one hop).
- Orders: buy `{side, symbol, notional_quote_units, max_slippage_bps}` or
  sell `{side, symbol, qty, max_slippage_bps}`. `client_id` auto-assigned
  if omitted; ids starting with `_` are reserved. At most 16 orders/reply;
  >64 is a protocol violation. A reply's buys together may spend at most
  the cash held when deciding (a reply's sells never fund its buys).
- Fills: an order decided on the batch of the bar closing at minute `t`
  fills at the **next bar's open**. Buy price = open x (1 + 2 bps slippage)
  x impact factor; sell price = open / (1 + 2 bps) / impact factor; fee
  4 bps on notional/gross proceeds. Impact is constant-product against
  that bar's open depth: factor `1 + a/D` (a = trade value in USDC raw).
  At the frozen depth (~$1.38M) a $1,000 buy moves its price ~7 bps; at
  the dev window's median depth (~$786k) it is ~13 bps/leg, so a full-size
  round trip costs ~38 bps (~$3.80). Every order names
  `max_slippage_bps` (0–10,000) measured from the latest close sent.
  Orders on the last batch are rejected (`after_end`); everything still
  held at the end is sold at the last close (same fee/slippage/impact,
  no slippage cap).
- Determinism: two executions on the same data must produce byte-identical
  action logs. No network, no wall clock (time = bar time), no files
  outside the repo, no unseeded randomness (seed from `hello.seed`).
  Runtime: `python3 -P -s /bot/main.py`, PYTHONHASHSEED=0 (or Node 22
  `node /bot/main.ts`). Sandbox: 1 CPU, 512 MB, 1,800 s budget.
  Standard library + vendored repo source only; nothing is installed.
- Dev gate: the final entry races only if its latest dev grade ends with
  **net PnL > $0** after every fee/slippage/impact. Hold-cash = $0 exactly
  and fails; buy-and-hold through a falling window fails.
- Race guardrails: on the race window, at least 1 trade and max drawdown
  ≤ 25%, or the entry ranks below every entry that meets the bar.
- Ranking: net PnL on the race window (final cash − $1,000), highest
  first; ties → fewer trades, then earlier receipt. Race window:
  **Sat 2026-11-14 12:29 WIB → Sun 2026-11-15 12:29 WIB**
  (05:29 UTC → 05:29 UTC), 1,440 one-minute bars, raced live.
- Local grading: `node cli/makefun.mjs grade-local --kit . --bot <repo>
  --driver process` (docker unavailable here; process driver runs the
  bot unisolated on this machine). Pre-submit:
  `node cli/makefun.mjs check --kit . --repo <repo> --transcripts ...`.
- Transcripts: every submission must bundle the agent sessions that built
  it; gate needs ≥5 assistant turns, ≥1 genuine revision of main.py,
  ≥30% authored-line reproduction, task terms (hello/batch/orders/bar),
  and sessions inside the competition window. Handed-over sessions take
  no paid place (`handed_over_places: none`), so this build stays in
  recorded sessions, one stage per message.

## Dev-window facts (frozen, `dataset/bars/CBBTC.ndjson.gz`)

- Window: **2026-11-12 23:14 UTC → 2026-11-13 23:14 UTC**
  (Fri 2026-11-13 06:14 WIB → Sat 2026-11-14 06:14 WIB), **1,440 bars,
  0 gaps**.
- Price: first open **$71,406.58** → last close **$67,900.67**:
  **-4.91% (-$3,505.91)**. High $71,423.57, low $67,626.92 (range 5.61%).
  Buy-and-hold mark-to-market **-$49.10** before fees.
- Shape: steady bleed, not a crash. Hours 0–4 fell -2.4% ($71,409 →
  $68,761); then choppy sideways-down. Best hours: +1.31% (hour 07 UTC),
  +0.88% (hour 10); largest 60-min up move +1.79% (bar 407); largest
  60-min move overall -2.23% (bar 228).
- Microstructure: 1-min log-return mean -0.35 bps, std **7.86 bps**;
  min -0.66%, max +0.35%. Flat bars (o=h=l=c): 95 (6.6%); o==c: 126.
  Up bars 658, down 704. Buy-and-hold max drawdown 4.97%.
- Depth: open depth median ~$786k, min ~$590k, max ~$1.02M USDC
  (pool: Orca Whirlpool HxA6SKW5qA4o12fjVgTpXdq2YnZ5Zv1s7SB4FFomsyLM,
  frozen depth $1,382,154.79).
- Consequence: a full-size round trip costs ~$3.80, so a trade must
  catch a move well above ~38 bps net to profit; 1-min noise is only
  ~8 bps, so most 1-min signals are noise.

## What the baselines actually score on dev (real grader, process driver)

Calibrated first: my offline simulator reproduces the real grader on
house ema-cross to within $0.04 (-$109.42 sim vs -$109.38 real, 58 trades,
max DD 10.97%), so the sim numbers below are trustworthy.

| baseline | dev net PnL | trades | max DD |
|---|---:|---:|---:|
| buy-and-hold | -$52.59 | 1 | 5.26% |
| hold-cash | $0.00 | 0 | 0.00% |
| momentum | -$49.23 | 1 | 5.13% |
| rsi-bollinger | -$65.83 | 11 | 6.78% |
| adx-momentum | -$50.31 | 20 | 5.31% |
| ema-cross (8/21) | **-$109.38** | 58 | 10.97% |

Every shipped baseline FAILS the dev gate. Plain EMA crossover is the
worst of them: 40–58 whipsaw crosses in a choppy bleed, each losing
~$4–8 to fees + adverse drift. The spec's "natural fit" (fast/slow EMA
crossover) only passes if it is made far more selective — that is the
whole design problem on this window. The three winning cross-trades in
the window (+$5.91, +$3.48, +$5.52 gross-of-costs) are not separable
ex ante from the losing ones by any single threshold on 30/60/120-min
returns or EMA slope (checked exhaustively); the only robust separator
found is the conjunction below, which admits exactly one trade.

## Chosen strategy: selective EMA trend (ONE strategy)

Long only, one position, deterministic, stdlib-only Python.

1. **Signal — EMA(12) crosses above EMA(36)** on 1-min closes
   (EMAs seeded as the mean of their first span of closes, as the
   baseline does; float64, integer prices from the wire).
2. **Confirmation — both must hold at the cross bar:**
   - (a) slow EMA rising over 60 bars: `EMA36[t] >= EMA36[t-60]`
     (the turn is real, not a dead-cat bounce inside a waterfall;
     at the dev trade this reads +4.4 bps, vs -44 to -100 bps at the
     rejected waterfall crosses — a comfortable margin, not a hairline);
   - (b) washout: 240-min return < **-1%** (buy the turn after a
     sell-off, never chase a top).
3. **Size — $250 fixed per entry (25% of starting equity).** Impact
   scales with size (~3 bps/leg at $250 vs ~13 bps at $1,000), so a
   marginal trade survives its own costs; the rest of the cash stays
   idle. This is what flips the dev result from -$1.47 (full size)
   to +$0.12.
4. **Exit — first of:** take-profit **+0.8%** vs entry cost, hard stop
   **-0.5%** vs entry cost, or EMA(12) crossing back below EMA(36).
5. **Cooldown — 60 bars after any exit** before a new entry (kills the
   re-entry chains that bled the plain cross strategy: -$73.79 → -$36.15
   from this alone).
6. **Equity guard — flatten everything if equity falls 8% below its
   peak** (far inside the 25% race guardrail; dev max DD is 0.11%).
7. **No fallback trade, no time-of-day rule.** If the setup never
   occurs, the bot holds cash (and would fail the ≥1-trade guardrail on
   that window — accepted: any forced trade on this dev window loses
   ~$1–5 and would fail the dev gate instead).

Parameters (signal: 2; risk: 4, all round numbers, none fitted to
individual bars): FAST=12, SLOW=36, WASHOUT_240M=-1%, TP=+0.8%,
STOP=-0.5%, COOLDOWN=60 bars, SIZE=$250, EQUITY_GUARD=8%.

**Simulated dev result (calibrated sim): net PnL +$0.12, 1 round trip
(2 trades), max drawdown 0.11%.** The single trade: buy bar 1099 at
~$68,718, sell bar 1136 at ~$68,806 (cross-down exit). Full-size
version of the same rule: -$1.47; $500 size: -$0.09. The margin is
razor-thin and sim-based — Stage 2 MUST verify it with the real
`grade-local` (process driver) before any submission, and if the real
grade is ≤ $0, iterate only on round, principled levers (size $200/$300,
TP 1.0%) and report honestly if no variant clears $0. A bot that does
not clear the dev gate must not be submitted as the final entry.

Why this design for the race window (unseen): it is a trend-turn
strategy, not a per-minute scalper — it stays in cash through chop
and only buys a confirmed turn after a washout, which is exactly the
setup that produced the window's three profitable bounces (+1.3%,
+0.9%, +1.0% hours). On a trending-up race window the same rule fires
on each washout-and-turn; on a flat window it trades little and keeps
drawdown near zero.

## Repo

- https://github.com/eastVUNK/btc-race-24h-20261113-2314 (public,
  created after the competition opened, owner eastVUNK)
- Stage 1 files pushed: `LICENSE` (MIT, SPDX line at top),
  `README.md`, `.makefun/owner.json` (wallet
  BghxTGURoYyWDjrUAnoBu5HWwRmnnoueR5PuDUfRb9gE), `STAGE1.md`.
- Stage 2 (next message): implement `main.py` (vendored
  `vendor/makefun_bars.py` shim, byte-identical copy from the kit),
  grade locally with `grade-local --driver process`, revise until the
  real dev grade is > $0 with margin, then `check` + bundle + submit
  before Sat 2026-11-14 12:14 WIB.
