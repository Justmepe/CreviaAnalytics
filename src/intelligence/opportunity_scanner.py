"""
Opportunity Scanner

Scans all tracked assets and ranks them by a composite score based on:
- Trade setup confidence (from TradeSetupGenerator)
- R/R ratio of best setup
- Alignment with current regime
- Volume profile (volume vs market cap ratio)
- Price momentum (24h change direction vs setup direction)

Outputs ranked opportunities with recommendations.
"""

from typing import Dict, Any, List, Optional


# Regime alignment scoring — which directions align with which regimes
REGIME_DIRECTION_ALIGNMENT = {
    'RISK_ON': {'LONG': 1.0, 'SHORT': -0.5},
    'ACCUMULATION': {'LONG': 0.8, 'SHORT': -0.3},
    'ALTSEASON_CONFIRMED': {'LONG': 0.9, 'SHORT': -0.4},
    'NEUTRAL': {'LONG': 0.0, 'SHORT': 0.0},
    'DISTRIBUTION': {'LONG': -0.3, 'SHORT': 0.8},
    'RISK_OFF': {'LONG': -0.5, 'SHORT': 1.0},
    'VOLATILITY_EXPANSION': {'LONG': 0.0, 'SHORT': 0.0},
}


class OpportunityScanner:
    """Scans and ranks trading opportunities across all tracked assets."""

    def scan_opportunities(
        self,
        setups: List[Dict[str, Any]],
        regime: Optional[Dict[str, Any]] = None,
        prices: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Score and rank all assets with active trade setups.

        Args:
            setups: List of trade setup dicts (from TradeSetupGenerator)
            regime: Current regime detection result
            prices: Dict of ticker → price_data for volume/momentum scoring

        Returns:
            Dict with ranked opportunities and summary picks
        """
        if not setups:
            return {
                'opportunities': [],
                'best_rr': None,
                'highest_conviction': None,
                'safest_play': None,
                'scanned_at': None,
            }

        regime_name = regime.get('regime', 'NEUTRAL') if regime else 'NEUTRAL'
        regime_confidence = regime.get('confidence', 0.5) if regime else 0.5

        scored = []
        for setup in setups:
            score_breakdown = self._score_setup(setup, regime_name, regime_confidence, prices)
            scored.append({
                'asset': setup.get('asset', '?'),
                'direction': setup.get('direction', '?'),
                'setup_type': setup.get('setup_type', ''),
                'confidence': setup.get('confidence', 0),
                'score': score_breakdown['composite'],
                'score_breakdown': score_breakdown,
                'best_rr': score_breakdown.get('best_rr', 0),
                'entry_zones': setup.get('entry_zones', []),
                'stop_loss': setup.get('stop_loss'),
                'take_profits': setup.get('take_profits', []),
                'reasoning': setup.get('reasoning', []),
                'risk_factors': setup.get('risk_factors', []),
                'regime_at_creation': setup.get('regime_at_creation'),
            })

        # Sort by composite score descending
        scored.sort(key=lambda x: x['score'], reverse=True)

        # Assign recommendations
        for i, opp in enumerate(scored):
            if opp['score'] >= 7.0:
                opp['recommendation'] = 'STRONG'
            elif opp['score'] >= 5.0:
                opp['recommendation'] = 'MODERATE'
            elif opp['score'] >= 3.0:
                opp['recommendation'] = 'WEAK'
            else:
                opp['recommendation'] = 'AVOID'

        # Pick summary roles
        best_rr = max(scored, key=lambda x: x['best_rr'], default=None)
        highest_conviction = max(scored, key=lambda x: x['confidence'], default=None)

        # Safest play = highest score with lowest risk (fewest risk factors, highest regime alignment)
        safest = max(
            scored,
            key=lambda x: x['score'] - len(x.get('risk_factors', [])) * 0.5,
            default=None,
        )

        from datetime import datetime, timezone
        return {
            'opportunities': scored,
            'opportunity_count': len(scored),
            'best_rr': {
                'asset': best_rr['asset'],
                'direction': best_rr['direction'],
                'rr': best_rr['best_rr'],
            } if best_rr else None,
            'highest_conviction': {
                'asset': highest_conviction['asset'],
                'direction': highest_conviction['direction'],
                'confidence': highest_conviction['confidence'],
            } if highest_conviction else None,
            'safest_play': {
                'asset': safest['asset'],
                'direction': safest['direction'],
                'score': safest['score'],
            } if safest else None,
            'regime': regime_name,
            'scanned_at': datetime.now(timezone.utc).isoformat(),
        }

    def _score_setup(
        self,
        setup: Dict[str, Any],
        regime_name: str,
        regime_confidence: float,
        prices: Optional[Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Score an individual setup on a 0-10 scale."""
        scores = {}

        # 1. Setup confidence (0-2.5 points)
        confidence = setup.get('confidence', 0)
        scores['confidence'] = min(confidence * 2.5, 2.5)

        # 2. R/R ratio (0-2.5 points)
        best_rr = 0
        for tp in setup.get('take_profits', []):
            rr = tp.get('rr', 0)
            if rr > best_rr:
                best_rr = rr
        # Scale: 1.5R = 1pt, 2R = 1.5pt, 3R = 2pt, 5R+ = 2.5pt
        if best_rr >= 5:
            scores['rr'] = 2.5
        elif best_rr >= 3:
            scores['rr'] = 2.0
        elif best_rr >= 2:
            scores['rr'] = 1.5
        elif best_rr >= 1.5:
            scores['rr'] = 1.0
        else:
            scores['rr'] = max(best_rr * 0.5, 0)

        # 3. Regime alignment (0-2.5 points)
        direction = setup.get('direction', 'LONG')
        alignment_map = REGIME_DIRECTION_ALIGNMENT.get(regime_name, {'LONG': 0, 'SHORT': 0})
        alignment = alignment_map.get(direction, 0)
        # Scale alignment (-0.5 to 1.0) to (0 to 2.5)
        scores['regime_alignment'] = max((alignment + 0.5) / 1.5 * 2.5, 0)
        # Boost if regime confidence is high
        scores['regime_alignment'] *= min(regime_confidence + 0.5, 1.0)

        # 4. Volume/momentum (0-2.5 points)
        ticker = setup.get('asset', '')
        price_data = prices.get(ticker, {}) if prices else {}
        volume_score = 0
        momentum_score = 0

        if price_data:
            # Volume profile: volume_24h / market_cap ratio
            vol = price_data.get('volume_24h', 0) or 0
            mcap = price_data.get('market_cap', 0) or 0
            if mcap > 0 and vol > 0:
                vol_ratio = vol / mcap
                if vol_ratio > 0.15:
                    volume_score = 1.25  # Very high volume
                elif vol_ratio > 0.08:
                    volume_score = 1.0
                elif vol_ratio > 0.04:
                    volume_score = 0.75
                else:
                    volume_score = 0.5

            # Momentum alignment: 24h change direction matches setup direction
            change_24h = price_data.get('price_change_24h', 0) or 0
            if direction == 'LONG' and change_24h > 0:
                momentum_score = min(abs(change_24h) / 5 * 1.25, 1.25)
            elif direction == 'SHORT' and change_24h < 0:
                momentum_score = min(abs(change_24h) / 5 * 1.25, 1.25)
            elif direction == 'LONG' and change_24h < -3:
                # Contrarian long on big dip — slight bonus for accumulation plays
                if regime_name in ('ACCUMULATION', 'RISK_ON'):
                    momentum_score = 0.5
            elif direction == 'SHORT' and change_24h > 3:
                # Contrarian short on big pump — slight bonus for distribution plays
                if regime_name in ('DISTRIBUTION', 'RISK_OFF'):
                    momentum_score = 0.5
        else:
            volume_score = 0.625  # Default mid-range if no data
            momentum_score = 0.625

        scores['volume_momentum'] = volume_score + momentum_score

        # Composite
        composite = sum(scores.values())
        scores['composite'] = round(min(composite, 10.0), 2)
        scores['best_rr'] = best_rr

        return scores


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("OPPORTUNITY SCANNER — Smoke Test")
    print("=" * 70)

    scanner = OpportunityScanner()

    mock_setups = [
        {
            'asset': 'BTC', 'direction': 'LONG', 'setup_type': 'Accumulation Breakout',
            'confidence': 0.72,
            'entry_zones': [{'price': 68500, 'type': 'aggressive', 'reason': 'Support'}],
            'stop_loss': {'price': 66500, 'reason': 'Below structure', 'distance_pct': 2.9},
            'take_profits': [
                {'price': 72000, 'percentage': 50, 'rr': 1.75, 'reason': 'Resistance'},
                {'price': 75000, 'percentage': 50, 'rr': 3.25, 'reason': 'ATH'},
            ],
            'reasoning': ['Accumulation regime', 'Funding reset'],
            'risk_factors': ['Macro uncertainty'],
        },
        {
            'asset': 'ETH', 'direction': 'LONG', 'setup_type': 'Range Low Bounce',
            'confidence': 0.58,
            'entry_zones': [{'price': 3200, 'type': 'conservative', 'reason': 'Range low'}],
            'stop_loss': {'price': 3050, 'reason': 'Below range', 'distance_pct': 4.7},
            'take_profits': [
                {'price': 3600, 'percentage': 100, 'rr': 2.67, 'reason': 'Range high'},
            ],
            'reasoning': ['ETH/BTC ratio improving'],
            'risk_factors': ['Gas fee competition', 'L2 rotation'],
        },
        {
            'asset': 'SOL', 'direction': 'SHORT', 'setup_type': 'Overextended Short',
            'confidence': 0.45,
            'entry_zones': [{'price': 180, 'type': 'aggressive', 'reason': 'At resistance'}],
            'stop_loss': {'price': 195, 'reason': 'Above ATH', 'distance_pct': 8.3},
            'take_profits': [
                {'price': 160, 'percentage': 100, 'rr': 1.33, 'reason': 'Support zone'},
            ],
            'reasoning': ['Overextended pump'],
            'risk_factors': ['Strong trend', 'Meme season'],
        },
    ]

    result = scanner.scan_opportunities(
        setups=mock_setups,
        regime={'regime': 'ACCUMULATION', 'confidence': 0.65},
        prices={
            'BTC': {'volume_24h': 35e9, 'market_cap': 1.35e12, 'price_change_24h': -1.2},
            'ETH': {'volume_24h': 15e9, 'market_cap': 380e9, 'price_change_24h': 0.5},
            'SOL': {'volume_24h': 3e9, 'market_cap': 80e9, 'price_change_24h': 8.2},
        },
    )

    print(f"\nScanned {result['opportunity_count']} opportunities")
    print(f"Regime: {result['regime']}")
    for opp in result['opportunities']:
        print(f"\n  {opp['direction']} {opp['asset']} — Score: {opp['score']}/10 ({opp['recommendation']})")
        bd = opp['score_breakdown']
        print(f"    Confidence: {bd['confidence']:.1f} | R/R: {bd['rr']:.1f} | Regime: {bd['regime_alignment']:.1f} | Vol/Mom: {bd['volume_momentum']:.1f}")
        print(f"    Best R/R: {opp['best_rr']:.1f}:1")

    if result['best_rr']:
        print(f"\nBest R/R: {result['best_rr']['direction']} {result['best_rr']['asset']} ({result['best_rr']['rr']:.1f}R)")
    if result['highest_conviction']:
        print(f"Highest Conviction: {result['highest_conviction']['direction']} {result['highest_conviction']['asset']} ({result['highest_conviction']['confidence']*100:.0f}%)")
    if result['safest_play']:
        print(f"Safest Play: {result['safest_play']['direction']} {result['safest_play']['asset']} (score: {result['safest_play']['score']:.1f})")

    print("\n" + "=" * 70)
