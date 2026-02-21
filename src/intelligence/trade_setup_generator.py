"""
Trade Setup Generator

Uses Claude API to generate actionable trade setups based on:
- Current market regime
- Asset price data (support/resistance proxies from 24h high/low)
- Derivatives data (funding, OI)
- Smart money signals

Outputs structured trade setups with entry zones, stop loss, take profits,
position sizing, reasoning, and risk factors.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class TradeSetupGenerator:
    """Generates Claude-powered trade setups from market data."""

    def __init__(self):
        self._api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self._model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
        self._enabled = bool(self._api_key) and HAS_ANTHROPIC

    def generate_setup(
        self,
        ticker: str,
        price_data: Dict[str, Any],
        regime: Optional[Dict[str, Any]] = None,
        derivatives: Optional[Dict[str, Any]] = None,
        smart_money: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a trade setup for the given asset.

        Args:
            ticker: Asset ticker (BTC, ETH, SOL, etc.)
            price_data: Dict with price_usd, price_change_24h, high_24h, low_24h, etc.
            regime: Current regime detection result
            derivatives: Derivatives data (funding, OI)
            smart_money: Smart money scan result

        Returns:
            Structured trade setup dict or None on failure
        """
        if not self._enabled:
            return None

        prompt = self._build_prompt(ticker, price_data, regime, derivatives, smart_money)

        try:
            client = anthropic.Anthropic(api_key=self._api_key)
            response = client.messages.create(
                model=self._model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text.strip()

            # Parse JSON from Claude's response
            setup = self._parse_response(text, ticker, price_data)
            if setup:
                setup['generated_at'] = datetime.now(timezone.utc).isoformat()
                setup['regime_at_creation'] = regime.get('regime', 'NEUTRAL') if regime else 'UNKNOWN'
            return setup

        except Exception as e:
            print(f"[TradeSetupGenerator] Error generating setup for {ticker}: {e}")
            return None

    def _build_prompt(self, ticker: str, price_data: dict,
                      regime: Optional[dict], derivatives: Optional[dict],
                      smart_money: Optional[dict]) -> str:
        """Build the Claude prompt with market context."""
        price = price_data.get('price_usd', 0)
        change_24h = price_data.get('price_change_24h', 0)
        high_24h = price_data.get('high_24h', price * 1.02)
        low_24h = price_data.get('low_24h', price * 0.98)

        context_parts = [
            f"Asset: {ticker}/USDT",
            f"Current Price: ${price:,.2f}",
            f"24h Change: {change_24h:+.2f}%",
            f"24h High: ${high_24h:,.2f}",
            f"24h Low: ${low_24h:,.2f}",
        ]

        if regime:
            context_parts.append(f"Market Regime: {regime.get('regime', 'NEUTRAL')} (confidence: {regime.get('confidence', 0)*100:.0f}%)")
            context_parts.append(f"Regime Description: {regime.get('description', '')}")

        if derivatives:
            if derivatives.get('btc_funding_rate') is not None:
                context_parts.append(f"BTC Funding Rate: {derivatives['btc_funding_rate']*100:.4f}%")
            if derivatives.get('total_open_interest') is not None:
                context_parts.append(f"Total OI: ${derivatives['total_open_interest']/1e9:.1f}B")
            if derivatives.get('total_liquidations_24h') is not None:
                total_liq = derivatives['total_liquidations_24h']
                long_liq = derivatives.get('liquidations_24h_long', 0.0) or 0.0
                short_liq = derivatives.get('liquidations_24h_short', 0.0) or 0.0
                
                if long_liq > 0 or short_liq > 0:
                    # Long/short data available
                    context_parts.append(f"24h Liquidations: ${total_liq/1e6:.1f}M (Longs: ${long_liq/1e6:.1f}M / Shorts: ${short_liq/1e6:.1f}M)")
                else:
                    # Data unavailable for split
                    context_parts.append(f"24h Liquidations: ${total_liq/1e6:.1f}M (long/short split unavailable - WebSocket not connected)")

        if smart_money:
            context_parts.append(f"Smart Money Sentiment: {smart_money.get('net_sentiment', 'NEUTRAL')}")

        context = "\n".join(context_parts)

        return f"""You are a professional crypto trading analyst. Generate a trade setup based on this market data.

MARKET DATA:
{context}

Generate a JSON trade setup with this exact structure (no markdown, just raw JSON):
{{
  "asset": "{ticker}",
  "direction": "LONG" or "SHORT",
  "setup_type": "short description of setup type",
  "confidence": 0.0 to 1.0,
  "entry_zones": [
    {{"price": number, "type": "aggressive", "reason": "..."}},
    {{"price": number, "type": "conservative", "reason": "..."}},
    {{"price": number, "type": "patient", "reason": "..."}}
  ],
  "stop_loss": {{"price": number, "reason": "...", "distance_pct": number}},
  "take_profits": [
    {{"price": number, "percentage": 50, "rr": number, "reason": "..."}},
    {{"price": number, "percentage": 50, "rr": number, "reason": "..."}}
  ],
  "reasoning": ["point 1", "point 2", "point 3", "point 4"],
  "risk_factors": ["risk 1", "risk 2", "risk 3"]
}}

Rules:
- Base direction on regime and market conditions
- Entry zones should be realistic relative to current price
- Stop loss should account for volatility and support/resistance
- Take profits should have realistic R/R ratios
- Confidence should reflect how aligned the setup is with market conditions
- Be specific with price levels, not vague
- If the regime is RISK_OFF or DISTRIBUTION, prefer SHORT or conservative entries
- If the regime is RISK_ON or ACCUMULATION, prefer LONG setups"""

    def _parse_response(self, text: str, ticker: str, price_data: dict) -> Optional[Dict[str, Any]]:
        """Parse Claude's JSON response into a structured setup."""
        try:
            # Try to find JSON in the response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                setup = json.loads(json_str)

                # Add position sizing for common risk amounts
                entry_price = setup.get('entry_zones', [{}])[0].get('price', price_data.get('price_usd', 0))
                sl_price = setup.get('stop_loss', {}).get('price', 0)
                if entry_price and sl_price:
                    stop_distance = abs(entry_price - sl_price)
                    if stop_distance > 0:
                        setup['position_sizing'] = {
                            'risk_100': round(100 / stop_distance, 4),
                            'risk_200': round(200 / stop_distance, 4),
                            'risk_500': round(500 / stop_distance, 4),
                        }

                return setup
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"[TradeSetupGenerator] Parse error for {ticker}: {e}")
        return None


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("TRADE SETUP GENERATOR — Live Test")
    print("=" * 70)

    gen = TradeSetupGenerator()
    if not gen._enabled:
        print("ERROR: ANTHROPIC_API_KEY not set or anthropic not installed")
    else:
        setup = gen.generate_setup(
            ticker='BTC',
            price_data={
                'price_usd': 69000,
                'price_change_24h': -1.5,
                'high_24h': 70200,
                'low_24h': 68500,
            },
            regime={
                'regime': 'ACCUMULATION',
                'confidence': 0.65,
                'description': 'Low volatility consolidation. Smart money likely accumulating.',
            },
        )

        if setup:
            print(f"\nSetup: {setup.get('direction')} {setup.get('asset')}")
            print(f"Type: {setup.get('setup_type')}")
            print(f"Confidence: {setup.get('confidence', 0)*100:.0f}%")
            print(f"\nEntry Zones:")
            for ez in setup.get('entry_zones', []):
                print(f"  ${ez['price']:,.2f} ({ez['type']}) — {ez['reason']}")
            print(f"\nStop Loss: ${setup.get('stop_loss', {}).get('price', 0):,.2f}")
            print(f"\nTake Profits:")
            for tp in setup.get('take_profits', []):
                print(f"  ${tp['price']:,.2f} ({tp['percentage']}%) — R/R: {tp['rr']}:1")
        else:
            print("ERROR: Failed to generate setup")

    print("\n" + "=" * 70)
