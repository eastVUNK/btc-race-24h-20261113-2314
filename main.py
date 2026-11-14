"""Selective EMA trend bot for make.fun btc-race-24h-20261113-2314.

Strategy (Stage 1 design, unchanged): long-only trend-turn bot on 1-minute
cbBTC/USDC closes.

- Signal: EMA(12) crosses above EMA(36).
- Confirmation, both required at the cross bar:
    (a) slow EMA rising over 60 bars: EMA36[t] >= EMA36[t-60];
    (b) washout: 240-minute return < -1% (close[t] * 100 < close[t-240] * 99).
- Size: $250 fixed per entry (250,000,000 quote units).
- Exit, first of: take-profit +0.8% vs entry cost, hard stop -0.5% vs
  entry cost, or EMA(12) crossing back below EMA(36).
- Cooldown: 60 bars after any exit before a new entry.
- Equity guard: flatten everything if equity falls 8% below its peak,
  and latch: once tripped, no new entries for the rest of the run
  (exits always stay possible). A guard that only flattens once would
  let the bot re-enter the same crashing market after the cooldown.

Protocol: agent-fun/bars-replay/v1, via the kit's vendored shim
(vendor/makefun_bars.py, byte-identical to sdk/makefun_bars.py).
Standard library only. No network, no wall clock, no files outside the
repository, no randomness: the same bars always produce the same orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

FAST_SPAN = 12
SLOW_SPAN = 36
SLOPE_BARS = 60
WASHOUT_BARS = 240
# Washout: 240-minute return below -1% (integer check, no floats).
WASHOUT_NUM = 99
WASHOUT_DEN = 100
SIZE_QUOTE_UNITS = 250_000_000  # $250 fixed per entry.
# Take-profit +0.8% / hard stop -0.5% vs entry cost (integer checks).
TP_NUM = 1008
TP_DEN = 1000
STOP_NUM = 995
STOP_DEN = 1000
COOLDOWN_BARS = 60
# Equity guard: flatten if equity falls below 92% of its peak.
GUARD_NUM = 92
GUARD_DEN = 100
MAX_SLIPPAGE_BPS = 100


class Ema:
    """One EMA: seeded as the mean of its first span of closes, then
    moving 2 / (span + 1) of the way to each new close (as the kit's
    ema-cross baseline does)."""

    def __init__(self, span):
        self.span = span
        self.warm = []
        self.value = None

    def step(self, close):
        if self.value is not None:
            self.value += (2.0 / (self.span + 1)) * (close - self.value)
            return
        self.warm.append(close)
        if len(self.warm) == self.span:
            self.value = sum(self.warm) / float(self.span)


class Series:
    """Per-symbol indicator state over 1-minute closes (raw integer
    prices, price_scale 5)."""

    def __init__(self):
        self.fast = Ema(FAST_SPAN)
        self.slow = Ema(SLOW_SPAN)
        self.closes = []       # raw integer closes, oldest first.
        self.slow_hist = []    # slow EMA value after each bar (or None).
        self.prev_gap = None   # fast - slow after the previous bar.

    def push(self, close):
        self.closes.append(close)
        self.fast.step(close)
        self.slow.step(close)
        self.slow_hist.append(self.slow.value)
        if self.fast.value is None or self.slow.value is None:
            return None
        return self.fast.value - self.slow.value

    def slope_rising(self):
        """Slow EMA at or above its value SLOPE_BARS bars ago."""
        if len(self.slow_hist) <= SLOPE_BARS:
            return False
        now = self.slow_hist[-1]
        then = self.slow_hist[-1 - SLOPE_BARS]
        return now is not None and then is not None and now >= then

    def washed_out(self):
        """240-minute return below -1% (integer cross-multiplication)."""
        if len(self.closes) <= WASHOUT_BARS:
            return False
        now = self.closes[-1]
        then = self.closes[-1 - WASHOUT_BARS]
        return now * WASHOUT_DEN < then * WASHOUT_NUM


SERIES = Series()
LAST_EXIT_SEQ = -10 ** 9
PEAK_EQUITY = 0
# Latched once the equity guard trips: no new entries afterwards.
GUARD_TRIPPED = False


def on_batch(state, batch):
    global LAST_EXIT_SEQ, PEAK_EQUITY, GUARD_TRIPPED
    if state.warming_up:
        return []
    bar = None
    for b in batch["bars"]:
        if b["symbol"] == SYMBOL:
            bar = b
            break
    if bar is None:
        # No fresh bar for our symbol this minute: a gap adds nothing.
        return []
    close = int(bar["c"])
    gap = SERIES.push(close)
    prev_gap = SERIES.prev_gap
    SERIES.prev_gap = gap

    if state.equity > PEAK_EQUITY:
        PEAK_EQUITY = state.equity

    # The guard is about equity, not about being in a position: evaluate
    # it every batch, so a slow bleed across losing round trips can trip
    # it even while flat. Once tripped it latches for the rest of the run.
    guard_hit = state.equity * GUARD_DEN < PEAK_EQUITY * GUARD_NUM
    if guard_hit:
        GUARD_TRIPPED = True

    held = state.positions.get(SYMBOL)
    if held is not None:
        value = state.value(SYMBOL, held.qty)
        cost = held.cost
        take_profit = value * TP_DEN >= cost * TP_NUM
        stop_hit = value * STOP_DEN <= cost * STOP_NUM
        cross_down = (
            gap is not None
            and prev_gap is not None
            and prev_gap >= 0
            and gap < 0
        )
        if guard_hit or take_profit or stop_hit or cross_down:
            LAST_EXIT_SEQ = state.seq
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": held.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []

    # Flat: only a confirmed cross-up entry, after the cooldown — and
    # never after the equity guard has tripped.
    if GUARD_TRIPPED:
        return []
    if state.seq - LAST_EXIT_SEQ < COOLDOWN_BARS:
        return []
    if gap is None or prev_gap is None:
        return []
    cross_up = prev_gap <= 0 < gap
    if not cross_up:
        return []
    if not SERIES.slope_rising():
        return []
    if not SERIES.washed_out():
        return []
    notional = SIZE_QUOTE_UNITS
    if notional > state.cash:
        notional = state.cash
    if notional < int(state.hello["fees"]["min_notional_quote_units"]):
        return []
    return [{
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": notional,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }]


makefun_bars.run(on_batch)
