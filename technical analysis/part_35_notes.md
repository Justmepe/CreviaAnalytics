# Part 35 — Training and Deploying Predictive Models
**Type:** Python ML | **Verdict:** MEDIUM — 72.88% win rate, confidence→position size, ATR SL/TP from ML
**URL:** https://www.mql5.com/en/articles/18985

## Model Pipeline (Production-Ready Pattern)
```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit
import joblib

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('model',  GradientBoostingClassifier(n_estimators=400, learning_rate=0.05, max_depth=3))
])

# TimeSeriesSplit — critical for financial data (no future leakage)
tscv = TimeSeriesSplit(n_splits=5)
pipeline.fit(X_train, y_train)
joblib.dump(pipeline, f'{symbol}_model.pkl')
```

## Signal Output with Confidence → Position Size
```python
def predict_signal(pipeline, features, entry_price, atr):
    proba  = pipeline.predict_proba(features)[0]
    signal = pipeline.predict(features)[0]
    conf   = max(proba)

    sl = entry_price - atr if signal == 'BUY' else entry_price + atr
    tp = entry_price + atr * 2 if signal == 'BUY' else entry_price - atr * 2

    return {'signal': signal, 'sl': sl, 'tp': tp, 'conf': conf}

def confidence_to_size_factor(conf: float) -> float:
    if conf >= 0.90: return 1.0
    if conf >= 0.70: return 0.75
    return 0.0   # skip below 70% confidence
```

## 72.88% Win Rate Validation
Boom 1000 Index, 30 days. GBC with RRR=2. This validates that ML-assisted entries improve on random (50%). Our existing gate chain (zone+structure+EMA+ADX+VWV) likely achieves similar win rates — ML could be a final confidence filter.

## TimeSeriesSplit is Critical
Standard train/test split leaks future data. TimeSeriesSplit folds chronologically:
```
Fold 1: train [0:200], test [200:250]
Fold 2: train [0:250], test [250:300]
...
```
Never use random_state or shuffle for financial time series — always TimeSeriesSplit.
