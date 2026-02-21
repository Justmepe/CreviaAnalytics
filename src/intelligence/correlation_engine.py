"""
Correlation Engine

Calculates Pearson correlation matrix between market metrics using
historical time-series data from the metrics API (Phase 2).
Identifies strongest relationships and generates interpretations.
"""

import os
import requests
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone


# Metrics to track correlations between
CORRELATION_METRICS = [
    'fear_greed_index',
    'total_liquidations_24h',
    'total_open_interest',
    'btc_funding_rate',
    'btc_dominance',
    'total_volume_24h',
    'btc_price',
]

# Human-readable short labels for the correlation matrix
METRIC_LABELS = {
    'fear_greed_index': 'Fear/Greed',
    'total_liquidations_24h': 'Liquidations',
    'total_open_interest': 'Open Interest',
    'btc_funding_rate': 'BTC Funding',
    'btc_dominance': 'BTC Dom',
    'total_volume_24h': 'Volume',
    'btc_price': 'BTC Price',
}

# Interpretation rules for strong correlations
CORRELATION_RULES: List[Dict[str, Any]] = [
    {
        'pair': ('total_open_interest', 'btc_funding_rate'),
        'when_positive': 'High OI + rising funding = leverage building, cascade risk elevated',
        'when_negative': 'OI diverging from funding = positioning shift underway',
    },
    {
        'pair': ('total_liquidations_24h', 'total_open_interest'),
        'when_positive': 'Liquidations tracking OI = overleveraged positions being flushed',
        'when_negative': 'Liquidations falling as OI rises = stable leverage growth',
    },
    {
        'pair': ('btc_dominance', 'fear_greed_index'),
        'when_positive': 'BTC dom rising with sentiment = flight to quality',
        'when_negative': 'BTC dom falling as sentiment rises = risk-on rotation to alts',
    },
    {
        'pair': ('btc_dominance', 'total_volume_24h'),
        'when_positive': 'Volume flowing into BTC = defensive positioning',
        'when_negative': 'Volume rising as BTC dom falls = capital rotating to alts',
    },
    {
        'pair': ('btc_price', 'total_open_interest'),
        'when_positive': 'Price and OI rising together = leveraged momentum, watch for overextension',
        'when_negative': 'Price diverging from OI = potential trend exhaustion',
    },
    {
        'pair': ('btc_price', 'fear_greed_index'),
        'when_positive': 'Price and sentiment aligned = trend confirmation',
        'when_negative': 'Price diverging from sentiment = potential reversal signal',
    },
    {
        'pair': ('total_liquidations_24h', 'fear_greed_index'),
        'when_positive': 'High liquidations + high fear = capitulation event possible',
        'when_negative': 'Liquidations rising in greed = overleveraged longs at risk',
    },
]


class CorrelationEngine:
    """
    Calculates real-time correlations between market metrics
    using historical data from the metrics time-series API.
    """

    def __init__(self, api_url: Optional[str] = None):
        self._api_url = (api_url or os.getenv('WEB_API_URL', '')).rstrip('/')
        self._api_secret = os.getenv('WEB_API_SECRET', 'crevia-internal-key')

    def _fetch_metric_history(self, metric: str, hours: int = 24) -> List[Tuple[datetime, float]]:
        """Fetch historical data points for a metric from the API."""
        if not self._api_url:
            return []
        try:
            url = f"{self._api_url}/api/intelligence/metrics/history"
            resp = requests.get(
                url,
                params={'metric': metric, 'hours': hours},
                headers={'x-api-secret': self._api_secret},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                points = data.get('points', [])
                return [
                    (p['captured_at'], p['value'])
                    for p in points
                    if p.get('value') is not None
                ]
        except Exception:
            pass
        return []

    def calculate_correlations(self, period_hours: int = 24) -> Dict[str, Any]:
        """
        Calculate Pearson correlation matrix between tracked metrics.

        Args:
            period_hours: How many hours of history to use (default 24h).

        Returns:
            Dict with:
                matrix: 2D list of correlation values
                labels: List of metric labels
                metric_keys: List of metric internal names
                strongest_pairs: List of strongest correlations
                interpretation: Summary text
                period_hours: Period used
                calculated_at: ISO timestamp
        """
        # Fetch historical data for each metric
        all_series: Dict[str, List[float]] = {}
        for metric in CORRELATION_METRICS:
            history = self._fetch_metric_history(metric, period_hours)
            if history:
                all_series[metric] = [v for _, v in history]

        # Need at least 2 metrics with data to correlate
        available_metrics = [m for m in CORRELATION_METRICS if m in all_series]
        if len(available_metrics) < 2:
            return self._empty_result(period_hours, "Insufficient historical data for correlation analysis. Need at least 2 metrics with history.")

        # Align series to same length (use the shortest)
        min_len = min(len(all_series[m]) for m in available_metrics)
        if min_len < 3:
            return self._empty_result(period_hours, "Not enough data points yet. Need at least 3 observations per metric.")

        # Build data matrix (rows=observations, cols=metrics)
        data_matrix = np.array([
            all_series[m][-min_len:]  # Take last N points for alignment
            for m in available_metrics
        ])  # Shape: (n_metrics, n_observations)

        # Calculate Pearson correlation matrix
        # Handle constant columns (zero std) gracefully
        n_metrics = len(available_metrics)
        corr_matrix = np.eye(n_metrics)
        for i in range(n_metrics):
            for j in range(i + 1, n_metrics):
                series_i = data_matrix[i]
                series_j = data_matrix[j]
                std_i = np.std(series_i)
                std_j = np.std(series_j)
                if std_i > 0 and std_j > 0:
                    corr = float(np.corrcoef(series_i, series_j)[0, 1])
                    if np.isnan(corr):
                        corr = 0.0
                    corr_matrix[i, j] = corr
                    corr_matrix[j, i] = corr

        # Build labels
        labels = [METRIC_LABELS.get(m, m) for m in available_metrics]

        # Find strongest pairs (|correlation| > 0.5)
        strongest_pairs = []
        for i in range(n_metrics):
            for j in range(i + 1, n_metrics):
                corr_val = corr_matrix[i, j]
                if abs(corr_val) > 0.5:
                    pair_key = (available_metrics[i], available_metrics[j])
                    note = self._interpret_pair(pair_key, corr_val)
                    strongest_pairs.append({
                        'metric1': labels[i],
                        'metric2': labels[j],
                        'metric1_key': available_metrics[i],
                        'metric2_key': available_metrics[j],
                        'correlation': round(corr_val, 2),
                        'strength': self._strength_label(corr_val),
                        'note': note,
                    })

        # Sort by absolute correlation (strongest first)
        strongest_pairs.sort(key=lambda p: abs(p['correlation']), reverse=True)

        # Generate interpretation
        interpretation = self._generate_interpretation(strongest_pairs)

        return {
            'matrix': [[round(float(v), 2) for v in row] for row in corr_matrix],
            'labels': labels,
            'metric_keys': available_metrics,
            'strongest_pairs': strongest_pairs[:10],  # Top 10
            'interpretation': interpretation,
            'period_hours': period_hours,
            'data_points': min_len,
            'calculated_at': datetime.now(timezone.utc).isoformat(),
        }

    def _strength_label(self, corr: float) -> str:
        """Classify correlation strength."""
        abs_corr = abs(corr)
        if abs_corr >= 0.8:
            return 'very_strong'
        elif abs_corr >= 0.6:
            return 'strong'
        elif abs_corr >= 0.4:
            return 'moderate'
        return 'weak'

    def _interpret_pair(self, pair_key: Tuple[str, str], corr_val: float) -> str:
        """Look up interpretation for a specific metric pair."""
        for rule in CORRELATION_RULES:
            rule_pair = rule['pair']
            if set(pair_key) == set(rule_pair):
                if corr_val > 0:
                    return rule['when_positive']
                else:
                    return rule['when_negative']

        # Generic interpretation
        direction = 'positively' if corr_val > 0 else 'negatively'
        strength = self._strength_label(corr_val)
        m1 = METRIC_LABELS.get(pair_key[0], pair_key[0])
        m2 = METRIC_LABELS.get(pair_key[1], pair_key[1])
        return f"{m1} and {m2} are {strength} {direction} correlated"

    def _generate_interpretation(self, strongest_pairs: List[Dict[str, Any]]) -> str:
        """Generate a summary interpretation from the strongest correlations."""
        if not strongest_pairs:
            return "No significant correlations detected. Metrics are moving independently."

        # Pick top 3 pairs for narrative
        top = strongest_pairs[:3]
        lines = []
        for pair in top:
            lines.append(f"{pair['metric1']} <> {pair['metric2']} ({pair['correlation']:+.2f}): {pair['note']}")

        summary = "; ".join(lines)

        # Add risk assessment
        risk_keywords = ['cascade', 'overleveraged', 'capitulation', 'exhaustion']
        has_risk = any(
            any(kw in pair.get('note', '').lower() for kw in risk_keywords)
            for pair in top
        )
        if has_risk:
            summary += ". Elevated risk signals detected — monitor closely."

        return summary

    def _empty_result(self, period_hours: int, reason: str) -> Dict[str, Any]:
        """Return an empty correlation result."""
        return {
            'matrix': [],
            'labels': [],
            'metric_keys': [],
            'strongest_pairs': [],
            'interpretation': reason,
            'period_hours': period_hours,
            'data_points': 0,
            'calculated_at': datetime.now(timezone.utc).isoformat(),
        }


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("CORRELATION ENGINE — Live Test")
    print("=" * 70)

    engine = CorrelationEngine()
    result = engine.calculate_correlations(period_hours=24)

    print(f"\nPeriod: {result['period_hours']}h")
    print(f"Data points: {result['data_points']}")
    print(f"Metrics: {result['labels']}")

    if result['matrix']:
        print("\nCORRELATION MATRIX:")
        labels = result['labels']
        header = f"{'':>14}" + "".join(f"{l:>12}" for l in labels)
        print(header)
        for i, row in enumerate(result['matrix']):
            line = f"{labels[i]:>14}" + "".join(f"{v:>12.2f}" for v in row)
            print(line)

    if result['strongest_pairs']:
        print(f"\nSTRONGEST PAIRS:")
        for pair in result['strongest_pairs']:
            print(f"  {pair['metric1']} <> {pair['metric2']}: {pair['correlation']:+.2f} ({pair['strength']})")
            print(f"    {pair['note']}")

    print(f"\nINTERPRETATION:")
    print(f"  {result['interpretation']}")

    print("\n" + "=" * 70)
    print("Done")
