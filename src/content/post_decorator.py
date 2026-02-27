"""
PostDecorator — append CTAs, hashtags, and site links to every post.

Rules (marketer-first):
  - X threads:    3–5 hashtags + site CTA on the FINAL tweet only
  - X articles:   one CTA block appended to body
  - Substack note: one-line CTA
  - Substack article: tags array + one CTA block at end of body
  - Mentions:     only when data source is explicitly that account (never gratuitous)
  - CTA wording:  rotate so it doesn't feel mechanical
  - Site link:    always https://creviacockpit.com
"""

import random
from typing import List, Optional, Tuple

SITE_URL = "https://creviacockpit.com"

# ── CTA variants (rotate) ─────────────────────────────────────────────────────

_X_CTA_TEMPLATES = [
    "Live data & signals → {url}",
    "Full breakdown + live charts → {url}",
    "Track this live → {url}",
    "Real-time regime detection → {url}",
    "Cockpit is live. Track it → {url}",
    "Full analysis on Crevia → {url}",
]

_SUB_NOTE_CTA_TEMPLATES = [
    "Live data → {url}",
    "Track it live → {url}",
    "Full analysis → {url}",
    "Cockpit → {url}",
]

_ARTICLE_CTA_BLOCKS = [
    (
        "\n\n---\n"
        "I tracked this live on **Crevia Cockpit** — real-time regime detection, "
        "whale flow scanner, and trade setups. Pro access is free while we're in early access.\n"
        "→ {url}"
    ),
    (
        "\n\n---\n"
        "**Track this in real time:** [Crevia Cockpit]({url}) — "
        "regime detection + whale scanner + live trade setups. "
        "Early Pro access still free."
    ),
    (
        "\n\n---\n"
        "**Want live signals?** Crevia Cockpit detects market regimes and whale flows "
        "before they're obvious. Free early access → {url}"
    ),
]

# ── Hashtag maps ──────────────────────────────────────────────────────────────

_X_TAG_MAP = {
    'BTC':    '#Bitcoin #BTC',
    'ETH':    '#Ethereum #ETH',
    'SOL':    '#Solana #SOL',
    'XRP':    '#XRP #Ripple',
    'DOGE':   '#Dogecoin #DOGE',
    'SHIB':   '#SHIB #ShibaInu',
    'PEPE':   '#PEPE #Memecoins',
    'FLOKI':  '#FLOKI #Memecoins',
    'XMR':    '#Monero #XMR',
    'ZEC':    '#Zcash #Privacy',
    'DASH':   '#Dash #Privacy',
    'AAVE':   '#Aave #DeFi',
    'UNI':    '#Uniswap #DeFi',
    'CRV':    '#Curve #DeFi',
    'LDO':    '#Lido #DeFi',
}

_X_SECTOR_TAGS = {
    'defi':     '#DeFi #DeFiNews',
    'memecoin': '#Memecoins #CryptoMeme',
    'privacy':  '#PrivacyCoins #Crypto',
    'macro':    '#Macro #CryptoTrading',
    'general':  '#Crypto #CryptoAnalysis #Trading',
}

_SUBSTACK_TAG_MAP = {
    'BTC':    ['bitcoin', 'crypto', 'trading'],
    'ETH':    ['ethereum', 'crypto', 'defi'],
    'SOL':    ['solana', 'crypto', 'altcoins'],
    'DOGE':   ['dogecoin', 'memecoins', 'crypto'],
    'XMR':    ['monero', 'privacy', 'crypto'],
    'defi':   ['defi', 'ethereum', 'crypto'],
    'macro':  ['macro', 'markets', 'crypto'],
}
_SUBSTACK_DEFAULT_TAGS = ['crypto', 'bitcoin', 'trading', 'markets', 'analysis']


# ── Public API ────────────────────────────────────────────────────────────────

class PostDecorator:
    """Attaches CTAs, hashtags, and site links to each content type."""

    def __init__(self, site_url: str = SITE_URL):
        self.site_url = site_url

    # ── X Thread ─────────────────────────────────────────────────────────────

    def decorate_x_thread(self, tweets: List[str], assets: List[str]) -> List[str]:
        """
        Append hashtags + CTA to the FINAL tweet only.
        Skips decoration if the last tweet is already over 200 chars
        (to avoid exceeding 280).
        """
        if not tweets:
            return tweets

        tags = self._pick_x_tags(assets)
        cta = random.choice(_X_CTA_TEMPLATES).format(url=self.site_url)

        last = tweets[-1].rstrip()
        appendix = f"\n\n{cta}\n\n{tags}"

        if len(last) + len(appendix) <= 280:
            tweets = list(tweets)
            tweets[-1] = last + appendix
        else:
            # Too long — append site link only (no tags)
            short = f"\n\n{cta}"
            if len(last) + len(short) <= 280:
                tweets = list(tweets)
                tweets[-1] = last + short
            # If still too long, leave untouched (content > url)

        return tweets

    # ── X Article ────────────────────────────────────────────────────────────

    def decorate_x_article(self, body: str, assets: List[str]) -> str:
        """Append a CTA block to the article body."""
        cta_block = random.choice(_ARTICLE_CTA_BLOCKS).format(url=self.site_url)
        return body.rstrip() + cta_block

    # ── Substack Note ────────────────────────────────────────────────────────

    def decorate_substack_note(self, note: str, assets: List[str]) -> str:
        """Append a one-line CTA."""
        cta = random.choice(_SUB_NOTE_CTA_TEMPLATES).format(url=self.site_url)
        return note.rstrip() + f"\n\n{cta}"

    # ── Substack Article ─────────────────────────────────────────────────────

    def decorate_substack_article(
        self,
        title: str,
        body: str,
        assets: List[str],
    ) -> Tuple[str, str, List[str]]:
        """
        Append a CTA block to the article body and return (title, body, tags).
        Tags go in Substack metadata, not embedded in body.
        """
        cta_block = random.choice(_ARTICLE_CTA_BLOCKS).format(url=self.site_url)
        decorated_body = body.rstrip() + cta_block
        tags = self._pick_substack_tags(assets)
        return title, decorated_body, tags

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _pick_x_tags(self, assets: List[str]) -> str:
        """Return 3–5 X hashtags based on the assets mentioned."""
        tags: List[str] = []

        # Add asset-specific tags (max 2)
        for a in assets[:4]:
            t = _X_TAG_MAP.get(a.upper())
            if t and t not in tags:
                tags.append(t)
                if len(tags) >= 2:
                    break

        # Add a general sector tag to reach 3
        if not tags:
            tags.append(_X_SECTOR_TAGS['general'])
        elif len(tags) < 3:
            tags.append(_X_SECTOR_TAGS['general'])

        # Flatten and deduplicate individual hashtags, cap at 5
        flat: List[str] = []
        seen = set()
        for group in tags:
            for ht in group.split():
                if ht not in seen and len(flat) < 5:
                    flat.append(ht)
                    seen.add(ht)

        return ' '.join(flat)

    def _pick_substack_tags(self, assets: List[str]) -> List[str]:
        """Return 4–6 Substack post tags based on the assets mentioned."""
        tags = list(_SUBSTACK_DEFAULT_TAGS)
        for a in assets[:3]:
            extra = _SUBSTACK_TAG_MAP.get(a.upper(), [])
            for t in extra:
                if t not in tags:
                    tags.append(t)

        return tags[:6]
