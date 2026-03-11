# Part 34 — Turning Raw Market Data into Predictive Models
**Type:** Python ML | **Verdict:** MEDIUM — feature engineering and labeling are the extracts
**URL:** https://www.mql5.com/en/articles/18979

## Spike Feature (Immediately Useful)
```python
# Simple spike flag using rolling range
df['range'] = df['high'] - df['low']
df['spike'] = (df['range'] > df['range'].rolling(50).mean() * 2).astype(int)
```
Better than our current VWV check for pure spike detection on Crash/Boom. Add alongside VWV.

## Labeling for Training Data
```python
LOOKAHEAD = 10   # bars
THRESH = 0.0015  # 0.15% move

def label_bars(df):
    df['label'] = 0
    for i in range(len(df) - LOOKAHEAD):
        future = df['close'].iloc[i + LOOKAHEAD]
        curr   = df['close'].iloc[i]
        move   = (future - curr) / curr
        if move >  THRESH: df.iloc[i, df.columns.get_loc('label')] = 1   # BUY
        if move < -THRESH: df.iloc[i, df.columns.get_loc('label')] = -1  # SELL
```

## GBC Hyperparameters (Validated)
```python
from sklearn.ensemble import GradientBoostingClassifier
model = GradientBoostingClassifier(n_estimators=400, learning_rate=0.05, max_depth=3)
```
400 trees, shallow (depth=3), low learning rate — prevents overfitting. Good defaults to start with.

## Feature Set for Our Signals (Upgrade Idea)
```python
features = {
    'spike':          df['spike'],          # Part 34
    'atr':            df['atr'],            # standard
    'rsi':            df['rsi'],
    'macd':           df['macd'],
    'crt_type':       df['crt_type'],       # Part 33 (encode: LR=3, NR=2, IB=1, SR=0, OB=-1)
    'zone_quality':   df['zone_quality'],   # from ZoneIdentifier
    'market_structure': df['ms_code'],      # BULLISH=1, BEARISH=-1, RANGING=0
    'ema_cross':      df['ema_cross'],      # 1=bullish cross, -1=bearish, 0=none
}
```
This could train a signal quality classifier: "given these features, is this a good entry?"
