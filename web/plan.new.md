Master Implementation Plan: Full Intelligence Platform
Context
The Crevia Analytics platform has ~20% of the plan.md vision built:

Done: Data pipeline, basic regime detection (5 regimes), regime API, MarketRegimeIndicator, IntelligentMetricCard (simplified), content publishing
Not built: Auth, subscriptions, correlation matrix, smart money tracker, risk calculator, trade setup generator, opportunity scanner, trade journal, real-time updates, charts, historical trend analysis
This plan addresses every gap between current state and plan.md, organized into 10 sequential phases. Each phase builds on the previous. Free APIs only — no CryptoQuant or Whale Alert.

Phase 1: DONE (Regime Detection + Intelligent Dashboard)
Already implemented. Files created:

src/intelligence/regime_detector.py
api/routers/intelligence.py
web/src/components/intelligence/MarketRegimeIndicator.tsx
web/src/components/intelligence/IntelligentMetricCard.tsx
Phase 2: Historical Metrics Storage + Enhanced Regime Detection
Why: The plan.md regime detector uses increasing/decreasing operators over time periods (24h, 7d). Our current detector only checks single-point thresholds. We need historical metric storage to enable trend detection, correlation calculations, and historical accuracy tracking.

2A: Historical Metrics Time-Series Table
MODIFY api/models/content.py — Add MetricTimeSeries model:


class MetricTimeSeries(Base):
    __tablename__ = 'metric_timeseries'
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(50), nullable=False)  # 'fear_greed_index', 'btc_dominance', etc.
    value = Column(Float, nullable=False)
    metadata_ = Column('metadata', JSONB)  # optional context
    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    # Composite index for fast range queries
    __table_args__ = (Index('idx_metric_ts', 'metric_name', 'captured_at'),)
MODIFY api/schemas/content.py — Add PublishMetricsRequest schema:


class MetricDataPoint(BaseModel):
    metric_name: str
    value: float
class PublishMetricsRequest(BaseModel):
    metrics: List[MetricDataPoint]
MODIFY api/services/content_service.py — Add:

save_metric_timeseries(db, metrics: list) — Bulk insert metric data points
get_metric_history(db, metric_name, hours_back) — Get historical values for trend calculation
get_metric_trend(db, metric_name, period_hours) — Returns {'direction': 'increasing'|'decreasing'|'flat', 'change_pct': float}
MODIFY api/routers/intelligence.py — Add:

POST /api/intelligence/metrics — Engine publishes batch metrics each cycle
GET /api/intelligence/metrics/history?metric={name}&hours={n} — Frontend/correlation reads history
GET /api/intelligence/metrics/trend?metric={name}&period={hours} — Get trend direction
MODIFY src/utils/web_publisher.py — Add publish_metrics(metrics_dict) method

MODIFY main.py — In research phase, after publishing snapshot, call publish_metrics() with all MarketMetrics fields as individual data points

2B: Enhanced Regime Detector
MODIFY src/intelligence/regime_detector.py:

Add ALTSEASON_CONFIRMED regime pattern (6th regime from plan.md)
Add _fetch_trend(metric, period_hours) method that queries API for trend data
Add trending operators: increasing, decreasing (compare current vs N hours ago)
Add volatile operator (std deviation > threshold over period)
Add percentile operator (current value vs historical distribution)
Track regime outcome history for accuracy scoring
MODIFY api/models/content.py — Add fields to RegimeSnapshot:

historical_accuracy (Float) — % of past similar regimes that played out
regime_count (Integer) — how many times this regime has been detected
previous_regime (String) — what regime preceded this one
MODIFY web/src/components/intelligence/MarketRegimeIndicator.tsx:

Show historicalAccuracy percentage
Show regime duration (computed from detected_at)
Add "View Past Regimes" link (to /intelligence/regimes page — Phase later)
Files for Phase 2:
Action	File
MODIFY	api/models/content.py — MetricTimeSeries model + RegimeSnapshot fields
MODIFY	api/schemas/content.py — MetricDataPoint, PublishMetricsRequest
MODIFY	api/services/content_service.py — time-series CRUD + trend calc
MODIFY	api/routers/intelligence.py — metrics endpoints
MODIFY	src/utils/web_publisher.py — publish_metrics()
MODIFY	main.py — publish metrics each cycle
MODIFY	src/intelligence/regime_detector.py — trending operators, ALTSEASON
MODIFY	web/src/components/intelligence/MarketRegimeIndicator.tsx — accuracy, duration
Phase 3: Correlation Matrix
Why: Plan.md Section 3.4. Shows real-time relationships between market metrics. Power users see raw correlations; the system uses them to strengthen regime confidence and generate insights.

3A: Correlation Calculation Engine (Python)
CREATE src/intelligence/correlation_engine.py:

CorrelationEngine class
calculate_correlations(period_hours=24) method:
Fetches historical metrics from API (Phase 2 endpoints)
Metrics: fear_greed_index, total_liquidations_24h, total_open_interest, btc_funding_rate, btc_dominance, total_volume_24h, exchange_netflow (if available)
Uses numpy/scipy to compute Pearson correlation matrix
Identifies strongest pairs (|correlation| > 0.6)
Generates interpretation text via simple rules:
High OI + High Funding → "Leverage building, cascade risk"
High BTC Dom + Capital outflows → "Risk-off rotation"
Returns: { matrix: [[float]], labels: [str], strongest_pairs: [{metric1, metric2, correlation, note}], interpretation: str }
MODIFY main.py — Call correlation engine every 15 minutes, publish results

3B: Correlation API + Storage
MODIFY api/models/content.py — Add CorrelationSnapshot:


class CorrelationSnapshot(Base):
    __tablename__ = 'correlation_snapshots'
    id, correlation_matrix (JSONB), strongest_pairs (JSONB),
    interpretation (Text), timeframe_hours (Integer),
    captured_at (DateTime, indexed)
MODIFY api/schemas/content.py — Add correlation schemas
MODIFY api/services/content_service.py — Add save/get correlation functions
MODIFY api/routers/intelligence.py — Add:

POST /api/intelligence/correlations — Engine publishes
GET /api/intelligence/correlations/latest?timeframe=24 — Frontend reads
3C: Correlation Matrix Frontend
CREATE web/src/app/intelligence/page.tsx — Intelligence hub page with:

Correlation matrix heat map
Strongest pairs list with interpretation
Current regime indicator (reuse component)
CREATE web/src/components/intelligence/CorrelationMatrix.tsx:

Client component (needs interactivity for hover tooltips)
Heat map grid using CSS (no D3 needed — simple colored cells)
Color scale: red (negative) → white (0) → green (positive)
Click cell to see detail
Strongest pairs section below with bars
Install: recharts for future chart needs (npm install recharts)

MODIFY web/src/types/index.ts — Add CorrelationSnapshot type
MODIFY web/src/lib/api.ts — Add getLatestCorrelations() function
MODIFY web/src/components/layout/Navbar.tsx — Add "Intelligence" nav link

Files for Phase 3:
Action	File
CREATE	src/intelligence/correlation_engine.py
CREATE	web/src/app/intelligence/page.tsx
CREATE	web/src/components/intelligence/CorrelationMatrix.tsx
MODIFY	api/models/content.py — CorrelationSnapshot
MODIFY	api/schemas/content.py — correlation schemas
MODIFY	api/services/content_service.py — correlation CRUD
MODIFY	api/routers/intelligence.py — correlation endpoints
MODIFY	src/utils/web_publisher.py — publish_correlations()
MODIFY	main.py — run correlation engine
MODIFY	web/src/types/index.ts — correlation types
MODIFY	web/src/lib/api.ts — getLatestCorrelations()
MODIFY	web/src/components/layout/Navbar.tsx — Intelligence nav
Phase 4: Smart Money Tracker (Free APIs)
Why: Plan.md Section 3.3. Tracks whale/institutional activity. Using FREE data sources only.

Available Free Signals:
Funding rates (Binance) — institutional positioning proxy
Liquidations (Binance WS) — cascade/stress events
OI changes (Binance) — leverage positioning
Large transactions (Etherscan API — already has key) — whale BTC/ETH transfers
Stablecoin market cap changes (CoinGecko) — new capital entering
Exchange volume anomalies (Binance) — unusual activity
4A: Smart Money Signal Aggregator (Python)
CREATE src/intelligence/smart_money_tracker.py:

SmartMoneyTracker class
scan_signals(global_metrics, derivatives_data) method:
Checks funding rate extremes (>0.05% or <-0.03%)
Checks liquidation spikes (>$100M in 1h)
Checks OI change (>5% in 24h)
Checks stablecoin supply changes (via CoinGecko global data)
Produces signal list with: type, asset, data, interpretation, impact (bullish/bearish/neutral), confidence
Generates netSentiment from signal aggregation
Generates aggregateInterpretation text
MODIFY src/data/aggregator.py — Add get_stablecoin_data() method (CoinGecko has USDT/USDC market cap data for free)

4B: Smart Money API + Storage
MODIFY api/models/content.py — Add SmartMoneySignal:


class SmartMoneySignal(Base):
    __tablename__ = 'smart_money_signals'
    id, signal_type (String), asset (String), timestamp (DateTime),
    data (JSONB), interpretation (Text), impact (String), confidence (String),
    captured_at (DateTime, indexed)
MODIFY api/schemas/content.py — Add smart money schemas
MODIFY api/services/content_service.py — Add smart money CRUD
MODIFY api/routers/intelligence.py — Add:

POST /api/intelligence/smart-money — Engine publishes signals
GET /api/intelligence/smart-money/signals?window=6h — Frontend reads
4C: Smart Money Frontend
CREATE web/src/components/intelligence/SmartMoneyTracker.tsx:

Client component
Shows net sentiment badge (BULLISH/BEARISH/NEUTRAL with color)
Aggregate interpretation text
Signal cards with type icon, data, interpretation, impact badge
Time-based filtering (1h, 6h, 24h)
MODIFY web/src/app/intelligence/page.tsx — Add SmartMoneyTracker section
MODIFY web/src/types/index.ts — SmartMoneySignal type
MODIFY web/src/lib/api.ts — getSmartMoneySignals()

Files for Phase 4:
Action	File
CREATE	src/intelligence/smart_money_tracker.py
CREATE	web/src/components/intelligence/SmartMoneyTracker.tsx
MODIFY	src/data/aggregator.py — stablecoin data
MODIFY	api/models/content.py — SmartMoneySignal
MODIFY	api/schemas/content.py
MODIFY	api/services/content_service.py
MODIFY	api/routers/intelligence.py — smart money endpoints
MODIFY	src/utils/web_publisher.py — publish_smart_money()
MODIFY	main.py — run smart money tracker
MODIFY	web/src/app/intelligence/page.tsx
MODIFY	web/src/types/index.ts
MODIFY	web/src/lib/api.ts
Phase 5: Context-Aware Risk Calculator
Why: Plan.md Section 3.5. Position sizing tool that warns about current market conditions.

5A: Risk Calculator Frontend (Client Component)
CREATE web/src/app/tools/risk-calculator/page.tsx — Risk calculator page

CREATE web/src/components/tools/RiskCalculator.tsx:

Client component ('use client')
Input fields: Entry price, stop loss, take profit, leverage, risk amount ($)
Calculations (all client-side JS):
Position size = risk / (entry - stop)
R/R ratio = (target - entry) / (entry - stop)
Max loss = risk amount
Potential gain = risk * R/R
Notional value = position * entry
Liquidation price (based on leverage + maintenance margin)
Daily funding cost = notional * funding_rate
Market context warnings (fetched from API):
Current regime → warning if RISK_OFF/DISTRIBUTION
Current funding rate → cost warning if elevated
Current volatility (from liquidation levels) → stop width warning
Suggest adjusted stop/leverage based on conditions
Adjusted recommendation section: Modified parameters based on warnings
MODIFY web/src/components/layout/Navbar.tsx — Add "Tools" dropdown with Risk Calculator

5B: Market Context API
MODIFY api/routers/intelligence.py — Add:

GET /api/intelligence/market-context — Returns current regime + funding rates + liquidation levels + volatility assessment (aggregates data the calculator needs)
MODIFY web/src/lib/api.ts — Add getMarketContext() function

Files for Phase 5:
Action	File
CREATE	web/src/app/tools/risk-calculator/page.tsx
CREATE	web/src/components/tools/RiskCalculator.tsx
MODIFY	api/routers/intelligence.py — market-context endpoint
MODIFY	web/src/lib/api.ts — getMarketContext()
MODIFY	web/src/types/index.ts — MarketContext type
MODIFY	web/src/components/layout/Navbar.tsx — Tools nav
Phase 6: Trade Setup Generator
Why: Plan.md Section 3.6. AI-generated trade ideas based on regime + market data. This is the plan's primary "actionable" differentiator.

6A: Trade Setup Engine (Python + Claude)
CREATE src/intelligence/trade_setup_generator.py:

TradeSetupGenerator class
generate_setup(ticker, asset_data, regime, derivatives) method:
Gathers: current price, support/resistance (from 24h high/low, ATH%), funding, OI, regime
Sends structured prompt to Claude API:
"Given this market data for {ticker}, current regime is {regime}, generate a trade setup"
Claude returns: direction, setup_type, entry_zones, stop_loss, take_profits, reasoning, risk_factors
Calculates position sizing for $100/$200/$500 risk levels
Calculates confidence score from regime confidence + signal alignment
Returns structured TradeSetup dict
6B: Trade Setup API + Storage
MODIFY api/models/content.py — Add TradeSetup:


class TradeSetup(Base):
    __tablename__ = 'trade_setups'
    id, asset (String), direction (String), setup_type (String),
    confidence (Float), entry_zones (JSONB), stop_loss (Float),
    take_profits (JSONB), reasoning (JSONB), risk_factors (JSONB),
    position_sizing (JSONB), regime_at_creation (String),
    outcome (String, default='pending'),  # pending/hit_tp/hit_sl/invalidated
    created_at (DateTime), expires_at (DateTime)
MODIFY api/schemas/content.py — Add setup schemas
MODIFY api/services/content_service.py — Add setup CRUD
MODIFY api/routers/intelligence.py — Add:

POST /api/intelligence/setups — Engine publishes generated setups
GET /api/intelligence/setups/latest?asset=BTC&limit=5 — Frontend reads
POST /api/intelligence/setups/generate — On-demand generation (rate-limited)
6C: Trade Setup Frontend
CREATE web/src/components/intelligence/TradeSetupCard.tsx:

Shows: direction badge, setup type, confidence %, asset
Entry zones (aggressive/conservative/patient)
Stop loss with distance %
Take profits with R/R ratios
Position sizing table
Reasoning bullet points
Risk factors
Regime context
CREATE web/src/app/intelligence/setups/page.tsx — Trade setups page
MODIFY web/src/app/intelligence/page.tsx — Add latest trade setup preview
MODIFY web/src/types/index.ts — TradeSetup type
MODIFY web/src/lib/api.ts — getTradeSetups()

Files for Phase 6:
Action	File
CREATE	src/intelligence/trade_setup_generator.py
CREATE	web/src/components/intelligence/TradeSetupCard.tsx
CREATE	web/src/app/intelligence/setups/page.tsx
MODIFY	api/models/content.py — TradeSetup model
MODIFY	api/schemas/content.py
MODIFY	api/services/content_service.py
MODIFY	api/routers/intelligence.py — setup endpoints
MODIFY	src/utils/web_publisher.py — publish_trade_setup()
MODIFY	main.py — generate setups for tracked assets
MODIFY	web/src/app/intelligence/page.tsx
MODIFY	web/src/types/index.ts
MODIFY	web/src/lib/api.ts
Phase 7: Opportunity Scanner
Why: Plan.md Section 3.7. Multi-asset comparison ranked by R/R + confidence.

7A: Scanner Engine (Python)
CREATE src/intelligence/opportunity_scanner.py:

OpportunityScanner class
scan_opportunities(assets_data, regime, setups) method:
For each tracked asset (16 assets), score based on:
Setup confidence (from Phase 6)
R/R ratio of best setup
Alignment with current regime
Technical positioning (RSI proxy from price action)
Volume profile (volume vs avg)
Composite score 0-10
Rank by score descending
Generate "Best R/R", "Safest Play", "Highest Conviction" picks
Returns: [{asset, score, setup_summary, confidence, recommendation}]
7B: Scanner API + Frontend
MODIFY api/routers/intelligence.py — Add:

POST /api/intelligence/opportunities — Engine publishes scan results
GET /api/intelligence/opportunities/latest — Frontend reads
CREATE web/src/app/intelligence/scanner/page.tsx — Scanner page
CREATE web/src/components/intelligence/OpportunityCard.tsx — Individual opportunity card
MODIFY web/src/app/intelligence/page.tsx — Add top 3 opportunities preview

Files for Phase 7:
Action	File
CREATE	src/intelligence/opportunity_scanner.py
CREATE	web/src/app/intelligence/scanner/page.tsx
CREATE	web/src/components/intelligence/OpportunityCard.tsx
MODIFY	api/models/content.py — OpportunityScan model
MODIFY	api/routers/intelligence.py — opportunity endpoints
MODIFY	api/services/content_service.py
MODIFY	api/schemas/content.py
MODIFY	src/utils/web_publisher.py — publish_opportunities()
MODIFY	main.py — run scanner
MODIFY	web/src/app/intelligence/page.tsx
MODIFY	web/src/types/index.ts
MODIFY	web/src/lib/api.ts
Phase 8: Authentication & Subscriptions
Why: No monetization possible without auth. Required for trade journal, personalization, and tiered access.

8A: Auth Backend (FastAPI)
CREATE api/routers/auth.py — Auth endpoints:

POST /api/auth/register — Email + password registration
POST /api/auth/login — Returns JWT token
POST /api/auth/refresh — Refresh JWT
GET /api/auth/me — Current user profile
Password hashing via passlib[bcrypt]
JWT via python-jose[cryptography]
CREATE api/middleware/auth.py — JWT middleware:

get_current_user() dependency — extracts user from JWT
require_tier(min_tier) dependency — checks subscription tier
MODIFY api/models/user.py — User model already exists, just needs:

Ensure password_hash works with passlib
Add verify_password() and hash_password() utility functions
MODIFY api/main.py — Register auth router

8B: Tiered Access Control
MODIFY api/routers/content.py — Add tier checking to content feed:

Free: Content older than 6 hours
Pro: Content older than 1 hour
Enterprise: All content immediately
MODIFY api/routers/intelligence.py — Add tier gates:

Free: Regime indicator only (basic — 3 regimes)
Pro: Full regime + correlation + smart money + risk calculator + 3 setups/day
Enterprise: Everything unlimited + API access
8C: Auth Frontend
CREATE web/src/app/login/page.tsx — Login page
CREATE web/src/app/register/page.tsx — Registration page
CREATE web/src/components/auth/AuthProvider.tsx — Client context for JWT
CREATE web/src/lib/auth.ts — Auth utilities (login, register, token storage, logout)

MODIFY web/src/components/layout/Navbar.tsx — Show login/profile button
MODIFY web/src/app/layout.tsx — Wrap with AuthProvider

8D: Stripe Subscription (Basic)
MODIFY api/routers/auth.py — Add:

POST /api/auth/create-checkout — Creates Stripe checkout session
POST /api/auth/webhook — Stripe webhook handler (subscription created/canceled)
MODIFY web/src/app/pricing/page.tsx — Wire pricing buttons to Stripe checkout

Install (Python): pip install stripe passlib[bcrypt] python-jose[cryptography]

Files for Phase 8:
Action	File
CREATE	api/routers/auth.py
CREATE	api/middleware/auth.py
CREATE	web/src/app/login/page.tsx
CREATE	web/src/app/register/page.tsx
CREATE	web/src/components/auth/AuthProvider.tsx
CREATE	web/src/lib/auth.ts
MODIFY	api/models/user.py — password utils
MODIFY	api/main.py — register auth router
MODIFY	api/routers/content.py — tier gates
MODIFY	api/routers/intelligence.py — tier gates
MODIFY	web/src/components/layout/Navbar.tsx — auth UI
MODIFY	web/src/app/layout.tsx — AuthProvider
MODIFY	web/src/app/pricing/page.tsx — Stripe checkout
Phase 9: Trade Journal & Portfolio
Why: Plan.md Sections from Phase 3. Users track their trades and see performance.

9A: Trade Journal
MODIFY api/models/content.py — Add TradeJournalEntry:


class TradeJournalEntry(Base):
    __tablename__ = 'trade_journal'
    id, user_id (FK→users), setup_id (FK→trade_setups, nullable),
    asset, direction, entry_price, exit_price, stop_loss, take_profit,
    position_size, leverage, pnl, pnl_percentage,
    entry_timestamp, exit_timestamp, notes (Text),
    regime_at_entry, tags (ARRAY(String)),
    created_at
CREATE api/routers/journal.py — CRUD endpoints:

POST /api/journal/entries — Create entry
GET /api/journal/entries — List entries with filters
PUT /api/journal/entries/{id} — Update (close trade)
GET /api/journal/stats — Performance analytics (win rate, avg R/R, best setup types)
CREATE web/src/app/journal/page.tsx — Trade journal page
CREATE web/src/components/journal/JournalEntryForm.tsx — Add/edit trade form
CREATE web/src/components/journal/PerformanceStats.tsx — Win rate, P&L charts

9B: User Alerts (Basic)
MODIFY api/models/content.py — Add UserAlert:


class UserAlert(Base):
    __tablename__ = 'user_alerts'
    id, user_id (FK→users), alert_type (String),
    conditions (JSONB), is_active (Boolean),
    last_triggered (DateTime), created_at
Alert types: regime_change, price_level, smart_money_signal

Files for Phase 9:
Action	File
CREATE	api/routers/journal.py
CREATE	web/src/app/journal/page.tsx
CREATE	web/src/components/journal/JournalEntryForm.tsx
CREATE	web/src/components/journal/PerformanceStats.tsx
MODIFY	api/models/content.py — TradeJournalEntry, UserAlert
MODIFY	api/schemas/content.py — journal schemas
MODIFY	api/services/content_service.py — journal CRUD
MODIFY	api/main.py — register journal router
MODIFY	web/src/types/index.ts
MODIFY	web/src/lib/api.ts
MODIFY	web/src/components/layout/Navbar.tsx — Journal nav
Phase 10: Real-Time Updates & Polish
Why: Plan.md specifies WebSocket/SSE for live updates. Current ISR (60s) is too slow for a trading platform.

10A: Server-Sent Events (SSE)
CREATE api/routers/realtime.py:

GET /api/realtime/stream — SSE endpoint that pushes:
Price updates (when engine publishes new prices)
Regime changes (when regime shifts)
Smart money alerts (when significant signal detected)
Uses asyncio.Queue per connected client
Engine publishes events via internal pub/sub (simple in-memory for now)
CREATE web/src/hooks/useRealtimeStream.ts — Client hook:

Connects to SSE endpoint
Dispatches events to update UI components
Auto-reconnect on disconnect
10B: Charts & Visualizations
Install: npm install recharts (already planned in Phase 3)

CREATE web/src/components/charts/PriceChart.tsx — Simple line chart for asset price history
CREATE web/src/components/charts/MetricChart.tsx — Mini sparkline for metric trends

MODIFY web/src/app/asset/[ticker]/page.tsx — Add price chart
MODIFY web/src/components/intelligence/IntelligentMetricCard.tsx — Add sparkline trend

10C: Enhanced IntelligentMetricCard
MODIFY web/src/components/intelligence/IntelligentMetricCard.tsx:

Add trend prop: { direction: 'up'|'down'|'flat', change: number, period: string }
Add correlations prop: [{ metric: string, relationship: string, note: string }]
Add historicalPattern text
Sparkline chart showing last 24h of the metric
10D: Mobile Responsive Polish
MODIFY all pages — Ensure responsive at all breakpoints
MODIFY web/src/components/layout/Navbar.tsx — Mobile-friendly intelligence/tools nav

Files for Phase 10:
Action	File
CREATE	api/routers/realtime.py
CREATE	web/src/hooks/useRealtimeStream.ts
CREATE	web/src/components/charts/PriceChart.tsx
CREATE	web/src/components/charts/MetricChart.tsx
MODIFY	api/main.py — register realtime router
MODIFY	web/src/app/asset/[ticker]/page.tsx — price chart
MODIFY	web/src/components/intelligence/IntelligentMetricCard.tsx — trends, sparklines
MODIFY	Various pages — responsive polish
Implementation Order & Dependencies

Phase 1 ✅ DONE
  │
  ▼
Phase 2: Historical Metrics + Enhanced Regime
  │  (Foundation for Phases 3, 4, 6, 7)
  ▼
Phase 3: Correlation Matrix
  │  (Uses historical metrics from Phase 2)
  ├──────────────┐
  ▼              ▼
Phase 4:       Phase 5:
Smart Money    Risk Calculator
  │              │
  ▼              │
Phase 6: Trade Setup Generator
  │  (Uses regime, smart money, correlations)
  ▼
Phase 7: Opportunity Scanner
  │  (Uses setups from Phase 6)
  ▼
Phase 8: Auth & Subscriptions
  │  (Can be done earlier if monetization is priority)
  ▼
Phase 9: Trade Journal & Portfolio
  │  (Requires auth from Phase 8)
  ▼
Phase 10: Real-Time & Polish
Note: Phase 8 (Auth) can be moved earlier if monetization is the priority. It has no technical dependency on Phases 2-7 — it's sequenced late because the intelligence features need to exist before users will pay.

Full File Summary
New Files to Create (24 files):
File	Phase	Description
src/intelligence/correlation_engine.py	3	Correlation calculation
src/intelligence/smart_money_tracker.py	4	Smart money signal aggregation
src/intelligence/trade_setup_generator.py	6	Claude-powered trade setups
src/intelligence/opportunity_scanner.py	7	Multi-asset opportunity scoring
api/routers/auth.py	8	Auth endpoints
api/routers/journal.py	9	Trade journal CRUD
api/routers/realtime.py	10	SSE real-time stream
api/middleware/auth.py	8	JWT auth middleware
web/src/app/intelligence/page.tsx	3	Intelligence hub page
web/src/app/intelligence/setups/page.tsx	6	Trade setups page
web/src/app/intelligence/scanner/page.tsx	7	Opportunity scanner page
web/src/app/tools/risk-calculator/page.tsx	5	Risk calculator page
web/src/app/login/page.tsx	8	Login page
web/src/app/register/page.tsx	8	Register page
web/src/app/journal/page.tsx	9	Trade journal page
web/src/components/intelligence/CorrelationMatrix.tsx	3	Heat map component
web/src/components/intelligence/SmartMoneyTracker.tsx	4	Smart money panel
web/src/components/intelligence/TradeSetupCard.tsx	6	Trade setup display
web/src/components/intelligence/OpportunityCard.tsx	7	Opportunity card
web/src/components/tools/RiskCalculator.tsx	5	Calculator component
web/src/components/auth/AuthProvider.tsx	8	Auth context
web/src/components/journal/JournalEntryForm.tsx	9	Journal form
web/src/components/journal/PerformanceStats.tsx	9	Performance analytics
web/src/components/charts/PriceChart.tsx	10	Price line chart
web/src/components/charts/MetricChart.tsx	10	Mini sparkline
web/src/hooks/useRealtimeStream.ts	10	SSE client hook
web/src/lib/auth.ts	8	Auth utilities
Files to Modify (repeatedly across phases):
api/models/content.py — New models each phase
api/schemas/content.py — New schemas each phase
api/services/content_service.py — New CRUD functions each phase
api/routers/intelligence.py — New endpoints each phase
api/main.py — Register new routers
src/utils/web_publisher.py — New publish methods
main.py — Integrate new intelligence modules
web/src/types/index.ts — New TypeScript types
web/src/lib/api.ts — New API client functions
web/src/components/layout/Navbar.tsx — New nav items
web/src/app/page.tsx — Homepage enhancements
Verification (Per Phase)
Each phase should be verified before moving to the next:

Phase 2: Run engine → check metric_timeseries table populates → verify trend API returns direction
Phase 3: Run engine → check correlation_snapshots populates → visit /intelligence page → see heat map
Phase 4: Run engine → check smart_money_signals populates → see tracker on intelligence page
Phase 5: Visit /tools/risk-calculator → enter trade → see market warnings
Phase 6: Run engine → check trade_setups populates → visit /intelligence/setups
Phase 7: Run engine → check opportunities → visit /intelligence/scanner
Phase 8: Register user → login → see tier-gated content
Phase 9: Create journal entry → see stats → close trade
Phase 10: See live price updates via SSE → see sparklines on metrics
Full flow: npm run build succeeds with zero errors