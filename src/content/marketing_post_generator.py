"""
Marketing Post Generator — Hormozi-framework standalone sales posts for X/Twitter.

Generates 4 post types, each fired at a dedicated daily slot:
  1. pain_led     (09:00 UTC) — opens with trader pain, closes with CTA
  2. value_stack  (15:00 UTC) — $559 standalone value → $100 Pilot offer
  3. social_proof (21:00 UTC) — identity contrast: reactive vs proactive trader
  4. risk_reversal (01:00 UTC) — late-night trader hook + trial close

Content schedule is SEPARATE from the market-intelligence thread schedule.
Market threads, daily scans, and articles are NEVER touched here.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


class MarketingPostGenerator:
    """
    Generates Claude-powered standalone sales posts using the Hormozi Value Equation:
        Value = (Dream Outcome × Perceived Likelihood) ÷ (Time Delay × Effort & Sacrifice)

    Posts are single tweets or 2-tweet threads. Never confused with market threads.
    """

    SITE_URL = "creviacockpit.com"

    # Pilot tier value stack (from marketing_messaging.md)
    VALUE_ITEMS: List[tuple] = [
        ("AI trade setups — live",            "$97/mo"),
        ("Whale intelligence",                 "$147/mo"),
        ("Unlimited regime-triggered alerts",  "$67/mo"),
        ("Opportunity scanner",                "$77/mo"),
        ("Advanced risk calculator",           "$57/mo"),
        ("Instant memos & threads",            "$47/mo"),
        ("API + 90-day historical data",       "$67/mo"),
    ]
    TOTAL_VALUE = "$559/mo"
    PILOT_PRICE = "$100/mo"

    POSITIONING_LINE = (
        "Crevia Cockpit is the market intelligence layer serious traders "
        "add when they're done trading blind."
    )

    # Tier rotation for value_stack posts (Mon/Wed/Fri = Pilot, Tue/Thu = Observer, Sat/Sun = Command)
    TIER_ROTATION = {0: 'pilot', 1: 'observer', 2: 'pilot', 3: 'observer', 4: 'pilot', 5: 'command', 6: 'command'}

    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')

    # =========================================================================
    # Claude helper
    # =========================================================================

    def _call_claude(self, prompt: str, max_tokens: int = 700) -> Optional[str]:
        """Call Claude API and return text response, or None on failure."""
        if not self.api_key:
            return None
        model = os.getenv('CLAUDE_CONTENT_MODEL', 'claude-haiku-4-5-20251001')
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            print(f"[MarketingPostGenerator] Claude call failed: {e}")
            return None

    def _market_context_str(self, market_data: Dict[str, Any]) -> str:
        """Format live market data as a compact context string for Claude prompts."""
        btc = market_data.get('btc_price') or market_data.get('BTC', {}).get('price_usd')
        eth = market_data.get('eth_price') or market_data.get('ETH', {}).get('price_usd')
        regime = market_data.get('regime_name') or market_data.get('regime', 'NEUTRAL')
        fg = market_data.get('fear_greed_index', '?')
        btc_chg = market_data.get('btc_change_24h') or market_data.get('BTC', {}).get('change_24h')

        parts = []
        if isinstance(btc, (int, float)):
            parts.append(f"BTC ${btc:,.0f}")
        if isinstance(eth, (int, float)):
            parts.append(f"ETH ${eth:,.0f}")
        if isinstance(btc_chg, (int, float)):
            parts.append(f"BTC 24h {'+' if btc_chg >= 0 else ''}{btc_chg:.1f}%")
        parts.append(f"Regime: {str(regime).replace('_', '-')}")
        parts.append(f"Fear/Greed: {fg}")

        return " | ".join(parts) if parts else "Market data unavailable"

    # =========================================================================
    # 4 Post Type Generators
    # =========================================================================

    def generate_pain_led(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Type 1 — Pain-Led (09:00 UTC).
        Opens with a concrete trading pain. Closes with CTA to creviacockpit.com.
        Hormozi: pain is a stronger motivator than desire for gain.
        """
        market_ctx = self._market_context_str(market_data)

        prompt = f"""You are a crypto market copywriter applying Alex Hormozi's Value Equation.

Live market right now: {market_ctx}

Write a standalone X (Twitter) post for Crevia Cockpit at {self.SITE_URL}.

POST TYPE: Pain-Led (09:00 UTC slot)

Framework rules:
- OPEN with one concrete, gut-punch trading pain that crypto traders recognise (missed a move, wrong size, no context before the entry, realised after the fact, 3 hours on X for nothing)
- AMPLIFY the cost of NOT having the intelligence — not just missing profit, but the confidence damage
- BRIDGE to the outcome (not a feature list) — what clarity feels like when you have it
- CLOSE with ONE CTA: → {self.SITE_URL}
- Hashtags at the very end (max 3): #CryptoTrading #MarketIntelligence #BTC

Banned words: signals, follow us, copy trades, guru
Required vocabulary: intelligence, regime, whale flow, clarity, data

Tone: direct, peer-to-peer, zero fluff — like one serious trader talking to another

Reference CTAs to draw from (adapt freely, don't copy verbatim):
- "One Bad Trade Can Wipe Out 10 Winning Ones. Size Every Position Correctly in 30 Seconds."
- "The Market Doesn't Wait for You to Log In."
- "Know Exactly What the Market Is Doing — Before Your Next Trade."

Format: single tweet (≤260 chars) OR a 2-tweet thread (mark the split point with exactly: ---)

Output ONLY the post text. Zero commentary, zero labels, zero intro."""

        raw = self._call_claude(prompt)
        if not raw:
            return self._fallback_pain_led(market_data)

        return self._parse_post(raw, 'pain_led')

    def generate_value_stack(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Type 2 — Value Stack / Offer (15:00 UTC).
        Shows the $559 standalone value → $100 Pilot gap.
        Tier rotates by weekday: Pilot (Mon/Wed/Fri), Observer (Tue/Thu), Command (Sat/Sun).
        """
        weekday = datetime.now(timezone.utc).weekday()
        tier = self.TIER_ROTATION.get(weekday, 'pilot')

        if tier == 'pilot':
            stack_text = "\n".join([f"✦ {item} → {price}" for item, price in self.VALUE_ITEMS])
            tier_context = (
                f"Tier: PILOT / Premium — {self.PILOT_PRICE}\n"
                f"Value stack:\n{stack_text}\n"
                f"Total standalone: {self.TOTAL_VALUE} → You pay {self.PILOT_PRICE}\n"
                "Trial: 7 days free, no credit card"
            )
            cta_hint = f"Fly as a Pilot — 7 Days Free → {self.SITE_URL}"

        elif tier == 'observer':
            tier_context = (
                "Tier: OBSERVER / Basic — $20/mo\n"
                "Includes: Real-time risk calculator, 10 personalised alerts, "
                "market regime detection, all 16 assets live, market dashboard, "
                "analysis feed, weekly digest\n"
                "Trial: 3 days free, no credit card"
            )
            cta_hint = f"Start as an Observer — 3 Days Free → {self.SITE_URL}"

        else:  # command
            tier_context = (
                "Tier: COMMAND / Premium+ — $200/mo\n"
                "Includes: Everything in Pilot PLUS first-hour exclusive access "
                "(intelligence before all other tiers), custom analysis requests, "
                "unlimited API, priority support\n"
                "Trial: 14 days free, no credit card"
            )
            cta_hint = f"Trade at Command level — 14 Days Free → {self.SITE_URL}"

        prompt = f"""You are a crypto market copywriter applying Alex Hormozi's Grand Slam Offer.

Live market: {self._market_context_str(market_data)}

Write a standalone X (Twitter) post for Crevia Cockpit at {self.SITE_URL}.

POST TYPE: Value Stack / Offer (15:00 UTC slot)
Today's tier rotation: {tier.upper()}

{tier_context}

Framework rules:
- Lead with the value or contrast — make saying NO feel irrational
- Show the gap between what it's worth standalone vs what they pay
- Close with the trial offer (the risk reversal)
- ONE CTA hint to adapt: {cta_hint}
- Hashtags at end (max 3): #CryptoTrading #Bitcoin #MarketIntelligence

Banned words: signals, follow us, copy trades, guru

Format: 2-3 tweet thread is fine here (mark splits with exactly: ---)
If listing features, use ✦ bullets. Keep the total under ~700 chars across all tweets.

Output ONLY the post text. Zero commentary."""

        raw = self._call_claude(prompt, max_tokens=800)
        if not raw:
            return self._fallback_value_stack(tier)

        return self._parse_post(raw, 'value_stack')

    def generate_social_proof(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Type 3 — Social Proof / Identity (21:00 UTC).
        Identity contrast: reactive vs proactive trader.
        Repels wrong audience, magnetises right one.
        """
        regime = str(market_data.get('regime_name') or market_data.get('regime', 'NEUTRAL')).replace('_', '-')

        prompt = f"""You are a crypto market copywriter using identity-based positioning (Hormozi + Kennedy niche call-out).

Live market regime: {regime}
Live market: {self._market_context_str(market_data)}

Write a standalone X (Twitter) post for Crevia Cockpit at {self.SITE_URL}.

POST TYPE: Social Proof / Identity (21:00 UTC slot)

Framework rules:
- Contrast two trader types: the one refreshing X reading opinions vs the one with the data
- "Same market. Different outcomes. The difference is intelligence, not luck."
- REPEL the wrong person: "This isn't for beginners chasing pumps."
- ATTRACT the right person: "For traders who already know how to execute — and just need better intelligence to execute on."
- End with ONE CTA: → {self.SITE_URL}
- Hashtags at end (max 3): #CryptoTrading #TradingStrategy #Bitcoin

Banned words: signals, follow us, copy trades, guru

Reference framings to draw from (adapt freely):
- "Two traders are looking at this market right now. One is refreshing X, reading opinions. One has the regime data, whale flow, and a sized position. Same market. Different outcomes."
- "Not smarter. Better data."
- "Built for traders who are tired of reacting — and ready to start anticipating."

Format: single tweet (≤260 chars) OR 2-tweet thread (mark with ---)

Output ONLY the post text. Zero commentary."""

        raw = self._call_claude(prompt)
        if not raw:
            return self._fallback_social_proof(market_data)

        return self._parse_post(raw, 'social_proof')

    def generate_risk_reversal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Type 4 — Risk Reversal (01:00 UTC — late-night traders).
        Hormozi: the one who takes on the most risk wins the customer.
        """
        prompt = f"""You are a crypto market copywriter applying Hormozi's risk-reversal close.

Live market: {self._market_context_str(market_data)}

Write a standalone X (Twitter) post for Crevia Cockpit at {self.SITE_URL}.

POST TYPE: Risk Reversal (01:00 UTC — late-night traders)

Framework rules:
- OPEN by acknowledging the late-night trader (up at midnight, researching, watching)
- Make them feel SEEN, not judged — just understood
- Remove ALL risk from the decision: 7 days free for Pilot, 14 days free for Command, no card
- Hormozi's exact frame: "If the intelligence doesn't make your next trading decision clearer than anything you've used before — you pay nothing."
- Flip the burden: they have nothing to lose. Every cent of risk is on us.
- ONE CTA: → {self.SITE_URL}
- Hashtags at end (max 2): #CryptoTrading #Bitcoin

Banned words: signals, follow us, copy trades

Format: single tweet (≤260 chars) OR 2-tweet thread (mark with ---)

Output ONLY the post text. Zero commentary."""

        raw = self._call_claude(prompt)
        if not raw:
            return self._fallback_risk_reversal()

        return self._parse_post(raw, 'risk_reversal')

    # =========================================================================
    # Static fallbacks (when Claude is unavailable)
    # =========================================================================

    def _fallback_pain_led(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        btc = market_data.get('btc_price')
        btc_str = f"${btc:,.0f}" if isinstance(btc, (int, float)) else "$BTC"
        text = (
            f"You checked {btc_str}. You saw the move. You weren't in it.\n\n"
            "Not because you missed the chart — because you didn't know the regime had shifted.\n\n"
            "Know exactly what the market is doing before your next trade.\n"
            f"→ {self.SITE_URL}\n"
            "#CryptoTrading #MarketIntelligence #BTC"
        )
        return self._parse_post(text, 'pain_led')

    def _fallback_value_stack(self, tier: str = 'pilot') -> Dict[str, Any]:
        lines = [f"✦ {item} → {price}" for item, price in self.VALUE_ITEMS]
        text = (
            "Everything in the Crevia Cockpit Pilot tier:\n\n"
            + "\n".join(lines)
            + f"\n\nTotal standalone value: {self.TOTAL_VALUE}\nYou pay: {self.PILOT_PRICE}"
            + "\n\n7-day free trial. No credit card.\n"
            + f"→ {self.SITE_URL}\n"
            "#CryptoTrading #Bitcoin #MarketIntelligence"
        )
        return self._parse_post(text, 'value_stack')

    def _fallback_social_proof(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        text = (
            "Two traders. Same market.\n\n"
            "One is refreshing X, reading opinions.\n"
            "One has the regime data, whale flow, and a sized position.\n\n"
            "Same market. Different outcomes.\n\n"
            "The difference is intelligence, not luck.\n"
            f"→ {self.SITE_URL}\n"
            "#CryptoTrading #TradingStrategy #Bitcoin"
        )
        return self._parse_post(text, 'social_proof')

    def _fallback_risk_reversal(self) -> Dict[str, Any]:
        text = (
            "You're up late watching markets.\n\n"
            "Try Crevia Cockpit free — 7 days, no card. Whale flow, regime detection, AI trade setups.\n\n"
            "If the intelligence doesn't make your next decision clearer, you pay nothing.\n"
            f"→ {self.SITE_URL}\n"
            "#CryptoTrading #Bitcoin"
        )
        return self._parse_post(text, 'risk_reversal')

    # =========================================================================
    # Output formatter
    # =========================================================================

    def _parse_post(self, raw: str, post_type: str) -> Dict[str, Any]:
        """Parse raw Claude output (possibly multi-tweet via ---) into post dict."""
        tweets = [t.strip() for t in raw.split('---') if t.strip()]
        if not tweets:
            tweets = [raw.strip()]

        return {
            'post_type': post_type,
            'tweets': tweets,
            'tweet_count': len(tweets),
            'copy_paste_ready': '\n\n---\n\n'.join(tweets),
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }
