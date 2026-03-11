# Part 64 — Engineering Trading Discipline into Code (Part 1): Structural Discipline
**Type:** EA Architecture | **Verdict:** CRITICAL EXTRACT — IConstraint pattern, TryOpenOrder() gateway. Our system has NO daily trade count/profit/loss enforcement. This is a significant gap.
**URL:** https://www.mql5.com/en/articles/21273

## What This Is
Architectural pattern for enforcing trading rules programmatically. Three constraint types:
MaxTradesPerDay (frequency), DailyProfitTarget% (greed control), MaxDailyLoss% (risk protection).
All enforced through a single TryOpenOrder() gateway — no bypassing possible.

## IConstraint Interface Pattern
```python
from abc import ABC, abstractmethod
from datetime import datetime, date

class IConstraint(ABC):
    @abstractmethod
    def is_breached(self) -> bool:
        pass

    @abstractmethod
    def reset_if_new_day(self, today: date) -> None:
        pass

    @abstractmethod
    def update_on_transaction(self, pnl: float, is_entry: bool) -> None:
        pass

    @abstractmethod
    def reason(self) -> str:
        pass
```

## MaxTradesPerDay Constraint
```python
class MaxTradesConstraint(IConstraint):
    def __init__(self, max_trades: int = 5):
        self.max_trades = max_trades
        self._trade_count = 0
        self._last_day = None

    def reset_if_new_day(self, today: date) -> None:
        if today != self._last_day:
            self._trade_count = 0
            self._last_day = today

    def update_on_transaction(self, pnl: float, is_entry: bool) -> None:
        if is_entry:  # only count market entries, not exits
            self._trade_count += 1

    def is_breached(self) -> bool:
        return self._trade_count >= self.max_trades

    def reason(self) -> str:
        return f'MaxTradesPerDay: {self._trade_count}/{self.max_trades} reached'
```

## DailyProfitTarget Constraint
```python
class DailyProfitTargetConstraint(IConstraint):
    def __init__(self, target_pct: float = 2.0, account_balance: float = 10000):
        self.target_pct = target_pct
        self.account_balance = account_balance
        self._daily_pnl = 0.0
        self._last_day = None

    def reset_if_new_day(self, today: date) -> None:
        if today != self._last_day:
            self._daily_pnl = 0.0
            self._last_day = today

    def update_on_transaction(self, pnl: float, is_entry: bool) -> None:
        if not is_entry:
            self._daily_pnl += pnl

    def is_breached(self) -> bool:
        target = self.account_balance * self.target_pct / 100.0
        return self._daily_pnl >= target

    def reason(self) -> str:
        return f'DailyProfitTarget: {self._daily_pnl:.2f} >= {self.target_pct}% target'
```

## MaxDailyLoss Constraint
```python
class MaxDailyLossConstraint(IConstraint):
    def __init__(self, loss_limit_pct: float = 3.0, account_balance: float = 10000):
        self.loss_limit_pct = loss_limit_pct
        self.account_balance = account_balance
        self._daily_loss = 0.0
        self._last_day = None

    def reset_if_new_day(self, today: date) -> None:
        if today != self._last_day:
            self._daily_loss = 0.0
            self._last_day = today

    def update_on_transaction(self, pnl: float, is_entry: bool) -> None:
        if not is_entry and pnl < 0:
            self._daily_loss += abs(pnl)

    def is_breached(self) -> bool:
        limit = self.account_balance * self.loss_limit_pct / 100.0
        return self._daily_loss >= limit

    def reason(self) -> str:
        return f'MaxDailyLoss: {self._daily_loss:.2f} >= {self.loss_limit_pct}% limit'
```

## TryOpenOrder() Gateway
```python
class DisciplineEngine:
    def __init__(self, config: dict):
        balance = config.get('account_balance', 10000)
        self.constraints = [
            MaxTradesConstraint(config.get('max_trades_per_day', 5)),
            DailyProfitTargetConstraint(config.get('daily_profit_target_pct', 2.0), balance),
            MaxDailyLossConstraint(config.get('daily_loss_limit_pct', 3.0), balance),
        ]

    def try_execute(self, signal, execute_fn) -> bool:
        today = datetime.now().date()
        for c in self.constraints:
            c.reset_if_new_day(today)
            if c.is_breached():
                print(f'[DisciplineEngine] BLOCKED: {c.reason()}')
                return False
        # All constraints pass — execute
        result = execute_fn(signal)
        if result:
            for c in self.constraints:
                c.update_on_transaction(0.0, is_entry=True)
        return result

    def on_trade_closed(self, pnl: float):
        for c in self.constraints:
            c.update_on_transaction(pnl, is_entry=False)
```

## CreviaDeriv Integration
```python
# In TradingOrchestrator.__init__():
self.discipline = DisciplineEngine(DISCIPLINE_CONFIG)

# In execute_signal() — wrap with discipline gateway:
def execute_signal(self, signal):
    return self.discipline.try_execute(
        signal,
        lambda s: self._actual_execute(s)  # original execute logic
    )

# In DISCIPLINE_CONFIG (add to config.py):
DISCIPLINE_CONFIG = {
    'max_trades_per_day': 5,
    'daily_profit_target_pct': 2.0,
    'daily_loss_limit_pct': 3.0,
    'account_balance': 10000,
}
```

## Parameter Defaults
| Parameter | Default | Notes |
|-----------|---------|-------|
| MaxTradesPerDay | 5 | Total market entries per session |
| DailyProfitTarget | 2.0% | Stop trading after 2% gain |
| MaxDailyLoss | 3.0% | Hard stop after 3% drawdown |

## Why This Is Critical
Our system currently has no daily discipline enforcement. A bad day with multiple losing signals
can cascade unchecked. MaxDailyLoss=3% is the PROP FIRM standard (FTMO, Funded Next).
DailyProfitTarget=2% prevents over-trading on winning days (greed creep).

## Superior Version
1. Per-symbol trade counts (allow 2 per symbol, not just 5 global)
2. Streak protection: 3 consecutive losses on same symbol -> skip symbol for rest of day
3. Weekend: reset at session open, not midnight (for forex M-F)
4. Log all constraint breaches with reason to trade journal file