# Part 04 — Analytics Forecaster EA
**Series:** Price Action Analysis Toolkit Development  
**Type:** Expert Advisor | **Verdict:** BUILD | **Depends on:** Parts 1, 2, 3

---

## What It Does in One Sentence
Part 3 (Analytics Master EA) + one new function (`SendTelegramMessage`) + three new config params = Part 4. Every line of analysis code is identical to Part 3. The entire contribution of this article is the notification transport layer.

---

## What Is Actually New vs Part 3

### 3 New Config Parameters
| Param | Default | Purpose |
|---|---|---|
| `TelegramToken` | `"YOUR BOT TOKEN"` | API token from BotFather — authenticates HTTP requests |
| `ChatID` | `"YOUR CHART ID"` | Destination chat (personal or group) |
| `SendTelegramAlerts` | `true` | Master on/off — disable without touching code |

### 1 New Function — SendTelegramMessage
```
POST https://api.telegram.org/bot{TOKEN}/sendMessage
Content-Type: application/json
Body: {"chat_id": "{CHAT_ID}", "text": "{message}"}
```
Success = HTTP 200. Anything else = log the error code.

### 1 New Output Field — Pair Name
`Symbol()` prepended to the message. Part 3 had no pair name — fine when you're looking at the chart, useless when you receive a Telegram message at 3am and don't know which instrument it's for.

---

## The Architecture in Three Hops
```
MT5 EA → HTTP POST → Telegram Bot API → Telegram Chat (mobile/desktop)
```
That's it. Three hops, one function, 30 lines of code. Simple and effective.

---

## How to Set Up the Telegram Bot

### Creating the Bot
1. Open Telegram → Search `@BotFather`
2. Send `/newbot`
3. Choose a display name (anything)
4. Choose a username ending in `bot` (e.g. `MyForexAlertBot`)
5. Receive your API token — format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
6. **Store it securely** — treat it like a password

### Getting Your Chat ID
**Method 1 (easiest):** Search `@userinfobot` in Telegram → Send `/start` → It replies with your chat ID

**Method 2 (manual):** Send any message to your bot, then visit:
```
https://api.telegram.org/bot{YOUR_TOKEN}/getUpdates
```
Look for `"chat": {"id": 123456789}` in the JSON response

### MT5 Prerequisite
Tools → Options → Expert Advisors → Allow WebRequest for listed URL → Add `https://api.telegram.org`

Without this step, the WebRequest call will silently fail.

---

## Three Security Problems in the Original

### 1. Token in Plain Text (HIGH)
The bot token is stored as an MQL5 `input string` — visible in the EA properties dialog, exported `.set` files, and strategy tester logs. Anyone with access to the machine can steal the token and send messages from your bot.

**Our fix:** Store token in an encrypted config file. Never as a user-facing input parameter.

### 2. JSON Injection Risk (MEDIUM)
The message is embedded directly into the JSON string:
```
StringFormat("{\"chat_id\":\"%s\",\"text\":\"%s\"}", ChatID, message)
```
If the message contains a `"` or `\n` or `\` character, it will break the JSON. The Telegram API call will either fail silently or produce garbled output.

**Our fix:** Use a proper JSON serialiser. Escape all special characters before embedding. At minimum: `\ → \\`, `" → \"`, newline `→ \n`.

### 3. No Retry (LOW)
If the HTTP request times out or the network is down, the message is lost with a log entry. The EA won't try again until the next 2-hour cycle.

**Our fix:** Queue failed messages. Retry up to 3 times with exponential backoff (1s, 2s, 4s).

---

## What the Screenshots Show

- **Fig 2** (`image1-2.png`) — Architecture diagram. MT5 → Telegram Bot API → Chat. The three-hop flow visualised.
- **Fig 7** (`PAIR_NAME.PNG`) — The actual Telegram message. Plain text, newline-separated key:value pairs. `Pair: USDSEK` at the top. No markdown formatting — just raw text.
- **Fig 10** (`Integration_Result.gif`) — Animated. Messages arriving in Telegram in real time. End-to-end proof of working integration.
- **Fig 11** (`Telegram_Integration.png`) — **Most important image.** MT5 chart panel on the left, identical content in Telegram on the right. Confirms data integrity — nothing is lost or changed in transit.

---

## Our NotificationService — What We Build Instead

Rather than a single hardcoded `SendTelegramMessage` function, we build a proper channel-agnostic notification service:

```python
class NotificationService:
    channels: List[NotificationChannel]   # Telegram, webhook, email, sound
    queue: MessageQueue                   # Retry failed sends

    def send(message, event_type) -> bool:
        msg = Message(sanitise(message), event_type, symbol, timestamp)
        if is_duplicate(msg): return  # Don't repeat identical alerts
        for channel in enabled_channels:
            if not channel.send(msg):
                queue.enqueue(msg, channel)  # Retry later

class TelegramChannel(NotificationChannel):
    def send(msg) -> bool:
        for attempt in [0, 1, 2]:  # Max 3 tries
            if http.post(url, payload).ok: return True
            sleep(2 ** attempt)    # 1s, 2s, 4s backoff
        return False
```

Key improvements over the original:
- **Multi-channel** — send to Telegram AND webhook AND sound simultaneously
- **Deduplication** — don't fire if content matches last sent message
- **Retry with backoff** — 3 attempts before giving up
- **Sanitisation** — proper JSON escaping before embedding
- **Secure token** — read from env var or encrypted config

---

## What to Keep
- Telegram as the primary notification channel — widely used by traders, mobile-first
- The `SendTelegramAlerts` boolean toggle — clean on/off
- Pair name in the message — essential for multi-chart setups
- The HTTP POST approach — simple and works
- Separating the send function from the analysis logic

## What to Discard
- Plain-text input param for token storage
- Raw string embedding in JSON payload
- MQL5-specific `WebRequest`, `StringToCharArray` APIs
- No retry on failure

## What to Improve (our build adds these)
- Secure token storage
- Proper JSON serialisation with escaping
- Retry with exponential backoff
- Message deduplication
- Telegram Markdown formatting (bold direction, monospace prices)
- Multi-channel: same alert → Telegram + webhook + sound
- Selective alerting: option to only notify on direction change (not every 2-hour heartbeat)
- Message queue: persist unsent messages and deliver when connection restores

---

## Architecture — Only One New Component
The entire contribution of Part 4 to the architecture is `NotificationService`. Everything else is inherited from Part 3.

```
NotificationService
  └── TelegramChannel      (Part 4 — primary)
  └── WebhookChannel       (our addition)
  └── EmailChannel         (our addition)
  └── SoundChannel         (user-requested in Part 2 forum)
```

This one component serves many future parts. Any tool that needs to push an alert uses `NotificationService.send()`. The channel configuration is separate from the tool logic — clean separation.
