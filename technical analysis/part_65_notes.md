# Part 65 — Engineering Trading Discipline into Code (Part 2): Daily Trade Limit Enforcer
**Type:** EA Architecture | **Verdict:** CRITICAL EXTRACT — 3-state machine with CAUTION mode, pending order cancellation, position closure on breach.
**URL:** https://www.mql5.com/en/articles/21313

## What This Is
Extends Part 64 with a 3-state machine: ALLOWED/CAUTION/LIMIT. CAUTION is the amber warning zone
before hard limit. On LIMIT: cancel pending orders. Close any NEW positions immediately.
Positions opened before limit are NOT retroactively closed.

## 3-State Machine
```python
from enum import Enum

class DisciplineState(Enum):
    ALLOWED = 'allowed'
    CAUTION = 'caution'
    LIMIT   = 'limit'

def calc_state(trades_done: int, max_trades: int, amber: int = 2) -> DisciplineState:
    if trades_done >= max_trades:
        return DisciplineState.LIMIT
    if max_trades - trades_done <= amber:
        return DisciplineState.CAUTION
    return DisciplineState.ALLOWED
```

## Full DisciplineEngine with 3 States
```python
from datetime import datetime, date

class DisciplineEngineFull:
    def __init__(self, max_trades=5, amber=2, profit_target_pct=2.0,
                  loss_limit_pct=3.0, account_balance=10000):
        self.max_trades = max_trades
        self.amber = amber
        self.profit_target = account_balance * profit_target_pct / 100
        self.loss_limit    = account_balance * loss_limit_pct / 100
        self._trades_today = 0
        self._daily_pnl    = 0.0
        self._daily_loss   = 0.0
        self._last_day     = None
        self._state        = DisciplineState.ALLOWED

    def refresh(self, today=None):
        today = today or datetime.now().date()
        if today != self._last_day:
            self._trades_today = 0
            self._daily_pnl = self._daily_loss = 0.0
            self._last_day = today
        self._state = calc_state(self._trades_today, self.max_trades, self.amber)
        if self._daily_pnl >= self.profit_target: self._state = DisciplineState.LIMIT
        if self._daily_loss >= self.loss_limit:   self._state = DisciplineState.LIMIT
        return self._state

    def can_trade(self) -> bool:
        return self._state != DisciplineState.LIMIT

    def on_entry(self): self._trades_today += 1; self.refresh()
    def on_close(self, pnl: float):
        self._daily_pnl += pnl
        if pnl < 0: self._daily_loss += abs(pnl)
        self.refresh()
```

## State-Aware Behavior in EntryEngine
```python
def execute_with_discipline(signal, discipline):
    discipline.refresh()
    state = discipline._state

    if state == DisciplineState.LIMIT:
        return False  # hard stop

    if state == DisciplineState.CAUTION:
        # Only take best setups when near limit
        if signal.departure_strength < 3: return False
        if signal.risk_reward_ratio < 2.0: return False
        if not signal.is_impulsive: return False  # skip corrective trades

    return True  # ALLOWED or passing CAUTION filter
```

## Pending Order Cancellation on LIMIT
```python
def cancel_pending_orders(symbol: str, mt5):
    orders = mt5.orders_get(symbol=symbol) or []
    pending_types = {mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT,
                     mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_SELL_STOP}
    for o in orders:
        if o.type in pending_types:
            mt5.order_send({'action': mt5.TRADE_ACTION_REMOVE, 'order': o.ticket})
```

## Daily Reset with Session Anchor
```python
from datetime import datetime, timedelta

def get_day_start(session_start_hour=0, session_start_min=0) -> datetime:
    now = datetime.now()
    anchor = now.replace(hour=session_start_hour, minute=session_start_min,
                         second=0, microsecond=0)
    if now < anchor:
        anchor -= timedelta(days=1)  # before session start = prior day
    return anchor
```

## CAUTION Mode Filter Summary
| Filter | ALLOWED | CAUTION | LIMIT |
|--------|---------|---------|-------|
| departure_strength | >= 1 | >= 3 | Block all |
| min RRR | 1.5 | 2.0 | Block all |
| corrective trades | Yes | No | Block all |

## config.py Addition
```python
DISCIPLINE_CONFIG = {
    'max_trades_per_day': 5,
    'amber_threshold': 2,
    'daily_profit_target_pct': 2.0,
    'daily_loss_limit_pct': 3.0,
    'session_start_hour': 0,
    'account_balance': 10000,
}
```

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| MaxTradesPerDay | 5 | Hard limit |
| AmberThreshold | 2 | CAUTION when this many slots remain |
| DailyProfitTarget | 2.0% | Stop when profitable enough |
| MaxDailyLoss | 3.0% | FTMO/prop firm standard |

## Superior Version
1. Persist state: write daily_state.json per server on each update
2. Weekly loss limit: if cumulative weekly loss > 6%, pause 2 days
3. Cross-server: FTMO LIMIT triggers Deriv CAUTION (reduce exposure across all brokers)
4. CAUTION also skips synthetic spike zone trades (highest false-signal risk on Crash/Boom)
5. Streak protection: 3 consecutive losses in ALLOWED -> enter CAUTION regardless of count