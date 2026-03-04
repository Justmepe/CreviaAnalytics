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
        self._model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-6')
        self._enabled = bool(self._api_key) and HAS_ANTHROPIC

    def generate_setup(
        self,
        ticker: str,
        price_data: Dict[str, Any],
        regime: Optional[Dict[str, Any]] = None,
        derivatives: Optional[Dict[str, Any]] = None,
        smart_money: Optional[Dict[str, Any]] = None,
        ta_context: Optional[Dict[str, Any]] = None,
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

        prompt = self._build_prompt(ticker, price_data, regime, derivatives, smart_money, ta_context)

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
                if ta_context:
                    setup['ta_quality'] = ta_context.get('setup_quality', 0)
                    setup['ta_htf'] = ta_context.get('htf', '')
                    setup['ta_direction'] = ta_context.get('direction', '')
            return setup

        except Exception as e:
            print(f"[TradeSetupGenerator] Error generating setup for {ticker}: {e}")
            return None

    def _build_prompt(self, ticker: str, price_data: dict,
                      regime: Optional[dict], derivatives: Optional[dict],
                      smart_money: Optional[dict],
                      ta_context: Optional[dict] = None) -> str:
        """Build the Claude prompt with market context and optional TA analysis."""
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
                    context_parts.append(f"24h Liquidations: ${total_liq/1e6:.1f}M (Longs: ${long_liq/1e6:.1f}M / Shorts: ${short_liq/1e6:.1f}M)")
                else:
                    context_parts.append(f"24h Liquidations: ${total_liq/1e6:.1f}M (long/short split unavailable)")

        if smart_money:
            context_parts.append(f"Smart Money Sentiment: {smart_money.get('net_sentiment', 'NEUTRAL')}")

        # TA section — inject real structure/zone/filter data when available
        ta_section = self._build_ta_section(ta_context) if ta_context else ""

        context = "\n".join(context_parts)

        direction_rule = ""
        if ta_context and ta_context.get('direction') not in (None, 'UNKNOWN'):
            ta_dir = ta_context['direction']
            direction_rule = (
                f"- Technical structure is {ta_dir} — strongly prefer a {ta_dir} setup "
                f"unless regime or derivatives data contradicts it clearly."
            )
        else:
            direction_rule = (
                "- If the regime is RISK_OFF or DISTRIBUTION, prefer SHORT or conservative entries\n"
                "- If the regime is RISK_ON or ACCUMULATION, prefer LONG setups"
            )

        return f"""You are a professional crypto trading analyst. Generate a trade setup based on this market data.

MARKET DATA:
{context}
{ta_section}
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
- Entry zones must be grounded in the technical levels above (zones, key levels) — never arbitrary
- Stop loss must be placed beyond the nearest invalidation level (zone protection price or last swing)
- Take profits must align with structural targets (opposing zones, key swing highs/lows)
- Confidence = (TA quality score / 100) as a base; adjust up/down for regime + derivatives alignment
- Be specific with price levels, not vague
{direction_rule}"""

    def _build_ta_section(self, ta: dict) -> str:
        """Format TA context into a readable prompt section."""
        lines: List[str] = ["\nTECHNICAL ANALYSIS:"]

        # Structure
        struct = ta.get('structure', {})
        if struct.get('available'):
            lines.append(f"  Trend ({ta.get('htf', '')}): {struct.get('trend')} | ADX: {struct.get('adx')} | Health: {struct.get('health')}")
            kl = struct.get('key_levels', {})
            if kl.get('last_HH'):
                lines.append(f"  Key Levels: HH=${kl['last_HH']:,.2f}  HL=${kl.get('last_HL', 0) or 0:,.2f}  "
                             f"LH=${kl.get('last_LH', 0) or 0:,.2f}  LL=${kl.get('last_LL', 0) or 0:,.2f}")
            if struct.get('choch_is_fresh'):
                lines.append(f"  *** FRESH CHoCH ({struct.get('choch_direction', '').upper()}) — {struct.get('choch_bars_ago')} bars ago ***")
            if struct.get('macro_trend'):
                lines.append(f"  Macro Trend: {struct['macro_trend']} (confidence {struct.get('macro_confidence', 0)*100:.0f}%)")

        # Zones
        zones = ta.get('zones', {})
        bd = zones.get('best_demand')
        bs = zones.get('best_supply')
        if bd:
            lines.append(f"  Best Demand Zone: ${bd['price_bottom']:,.2f}–${bd['price_top']:,.2f} "
                        f"(quality={bd['quality_score']:.0f}/100, {bd['location_label']}, {bd['status']})")
        if bs:
            lines.append(f"  Best Supply Zone: ${bs['price_bottom']:,.2f}–${bs['price_top']:,.2f} "
                        f"(quality={bs['quality_score']:.0f}/100, {bs['location_label']}, {bs['status']})")
        lines.append(f"  Active Zones: {zones.get('active_count', 0)} | Broken: {zones.get('broken_count', 0)}")

        # Entry filters
        ef = ta.get('entry_filters', {})
        if ef:
            lines.append(f"  Entry Alignment ({ta.get('ltf', '')}): {ef.get('filters_passed', 0)}/{ef.get('filters_total', 5)} filters "
                        f"({ef.get('alignment_score', 0)}%) | RSI: {ef.get('rsi', 50):.0f}")
            vwap_info = ef.get('vwap', {})
            if vwap_info.get('vwap'):
                lines.append(f"  VWAP: ${vwap_info['vwap']:,.2f} ({vwap_info.get('note', '')})")
            adx_info = ef.get('adx', {})
            if adx_info:
                lines.append(f"  ADX: {adx_info.get('adx', 0)} ({adx_info.get('health', '')})")

        # Overall quality
        lines.append(f"  Setup Quality Score: {ta.get('setup_quality', 0)}/100")

        return "\n".join(lines) + "\n"

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
