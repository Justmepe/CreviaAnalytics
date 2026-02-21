# Substack Posting System: 3 Formats

## Overview

The Substack posting system supports **3 content types**:

1. **TEXT** - Long-form articles (500+ words, research, analysis)
2. **NOTE** - Quick updates (alerts, news, brief thoughts)
3. **THREAD** - Multi-part threads (like X/Twitter threads)

---

## 1. TEXT Format (Articles)

### Use Cases
- Research reports
- Market analysis
- In-depth guides
- Weekly newsletters
- Detailed strategies

### Code Example
```python
poster.post_text(
    title="Bitcoin Breakout: Technical Setup & Levels",
    body_text="""Bitcoin is forming a classic cup and handle pattern.
    
    Key Support Levels:
    • $38,500 - Major support
    • $35,000 - Critical support
    
    Resistance:
    • $42,000 - Daily resistance
    • $45,000 - Strong resistance
    
    On-chain metrics show whale accumulation up 50%.""",
    is_published=False  # Save as draft (True to publish)
)
```

### When to Use
- Content > 500 characters
- Has a title
- Needs formatting
- Substantial information

---

## 2. NOTE Format (Quick Updates)

### Use Cases
- Price alerts
- Breaking news
- Quick observations
- Announcements
- Brief thoughts

### Code Example
```python
poster.post_note("Bitcoin breaks above $42K on Fed news! Watch $45K next level 📈 $BTC")
```

### When to Use
- Quick updates (< 500 chars ideal)
- Time-sensitive
- No title needed
- Frequent posting

---

## 3. THREAD Format (Multi-part)

### Use Cases
- X/Twitter threads
- Educational threads
- Sequential narratives
- Step-by-step guides

### Code Example
```python
thread_text = """1/ Bitcoin's latest move reveals something important about market structure. Here's what the charts show...

2/ The accumulation pattern we see here typically precedes a 30-40% move. Historical precedent:
• 2017: Similar pattern → 2000% bull
• 2019: Similar pattern → 400% bull
• 2023: And now...

3/ What this means: Strong bullish setup. Watch the next 48 hours closely."""

poster.post_as_thread(thread_text)
```

### When to Use
- Multiple connected parts (2+ minimum)
- Sequential information
- Educational/narrative content
- From X/Twitter threads

---

## Auto-Detection System

The system automatically selects the right format:

```python
from src.utils.substack_content_router import ContentTypeRouter

router = ContentTypeRouter(poster)

# Auto-detects as THREAD (twitter source detected)
router.post(content=twitter_thread, source="twitter")

# Auto-detects as NOTE (alert detected)
router.post(content="Quick alert text", source="alert")

# Auto-detects as TEXT (research detected)
router.post(content=long_research, source="research")
```

**Detection Rules:**
- `source="twitter"` or `"x_thread"` → **THREAD**
- `source="research"` or `"analysis"` → **TEXT**
- `source="news"`, `"alert"`, `"memo"` → **NOTE**
- `content_length > 500` → **TEXT**
- Default → **NOTE**

---

## Practical Examples

### Example 1: Post a Market Alert
```python
# Quick update
poster.post_note("ALERT: Bitcoin breaks above $42K resistance! 📊 Watch for next move to $45K")
```

### Example 2: Post Market Analysis
```python
# Long-form article
title = "Weekly Crypto Market Analysis"
analysis = """
This week shows critical developments across the market.

Bitcoin Performance:
• Price action: Consolidation above $40K
• Volume: Increasing on higher timeframes
• On-chain: Major whale accumulation

Ethereum Dynamics:
• Trading range: $2,300-$2,500
• Institutional interest: Growing
• Staking rewards: Attractive relative to rates

What to Watch:
1. Fed policy announcements
2. Bitcoin options expiry data
3. Macroeconomic indicators
"""

poster.post_text(title=title, body_text=analysis, is_published=True)
```

### Example 3: Post a Twitter Thread
```python
# Repost X thread to Substack
thread = """1/ Bitcoin's S-curve adoption follows a predictable pattern. Let me break it down.

2/ First phase: Innovation (2009-2013)
- Nerds and cypherpunks
- < $1,000 price
- Almost nobody cares

3/ Second phase: Early adopters (2013-2017)
- Tech entrepreneurs get it
- Price enters 4-figure range
- Media starts covering it

4/ Third phase: Mass adoption (2017-present)
- Institutions entering
- Price goes exponential
- Regulations accelerating

5/ We're currently in phase 3. This is what everything looks like when billions of people start realizing what Bitcoin is."""

poster.post_as_thread(thread)
```

---

## Methods Reference

### `post_text(title, body_text, is_published=False)`
Long-form article posting
- **title** (required): Article title string
- **body_text** (required): Full article content (100+ chars)
- **is_published** (optional): True = publish, False = save as draft
- Returns: article_id or None

### `post_note(body_text)`
Quick update posting
- **body_text**: Short content (any length OK)
- Returns: note_id or None

### `post_as_thread(thread_content)`
Thread posting
- **thread_content**: Multi-part content (separated by newlines, 2+ parts)
- Returns: thread_id or None

---

## Content Type Decision Tree

```
START: I have content to post

├─ Is it from X/Twitter?
│  └─ YES → post_as_thread()
│
├─ Is it short (<200 words)?
│  └─ YES → post_note()
│     └─ Alert? → post_note("ALERT: ...")
│     └─ News? → post_note("Breaking: ...")
│
├─ Is it long analysis (>500 words)?
│  └─ YES → post_text(title, body)
│     └─ Market research? → post_text("Weekly Analysis", "...")
│     └─ Strategy guide? → post_text("How to...", "...")
│
└─ DEFAULT → post_note()
```

---

## Best Practices

### For TEXT Posts
✓ Use meaningful titles
✓ Break content into paragraphs
✓ Include headers/sections
✓ Add data if applicable
✓ Save as draft first

### For NOTE Posts
✓ Keep under 500 chars when possible
✓ Use emoji for clarity 📊📈🚨
✓ Write headlines, not essays
✓ Link to full analysis if complex

### For THREAD Posts
✓ Start with hook (tweet 1)
✓ Build sequentially (tweet 2+)
✓ Each tweet should add value
✓ End with call-to-action (final tweet)
✓ Minimum 2 parts, maximum ~10

---

## Implementation Status

| Method | Status | Ready |
|--------|--------|-------|
| `post_note()` | ✅ Complete | Yes |
| `post_text()` | ✅ Complete | Yes |
| `post_as_thread()` | ✅ Complete | Yes |
| `ContentTypeRouter` | ✅ Complete | Yes |
| Authentication | ✅ Complete | Yes |
| Rate Limiting | ✅ Complete | Yes (5/day) |

---

## Next Steps

1. **Choose your content type** based on what you're posting
2. **Use the appropriate method**:
   - `poster.post_text()` for articles
   - `poster.post_note()` for updates
   - `poster.post_as_thread()` for threads
3. **Or use auto-detection**:
   - `router.post(content, source="research")`
4. **Monitor results** - track engagement by format

---

## Quick Links

- **Authentication**: [SUBSTACK_SETUP.md](SUBSTACK_SETUP.md)
- **Content Types Detailed**: [SUBSTACK_CONTENT_TYPES.md](SUBSTACK_CONTENT_TYPES.md)  
- **Full Posting Guide**: [SUBSTACK_POSTING_GUIDE.md](SUBSTACK_POSTING_GUIDE.md)
- **Code Router**: [src/utils/substack_content_router.py](src/utils/substack_content_router.py)
