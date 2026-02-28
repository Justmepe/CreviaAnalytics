"""
WebPublisher — Publishes engine-generated content to the FastAPI backend.
Mirrors the DiscordNotifier pattern: same constructor, same error handling.
"""

import os
import requests
from typing import Optional, Dict, Any, List


class WebPublisher:
    """Publish crypto analysis content to the Crevia Analytics web API."""

    def __init__(self, api_url: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_url = (api_url or os.getenv('WEB_API_URL', '')).rstrip('/')
        self.api_secret = api_secret or os.getenv('WEB_API_SECRET', 'crevia-internal-key')
        self.enabled = bool(self.api_url)
        self.session = requests.Session()
        self.session.headers.update({'x-api-secret': self.api_secret})

    def _post(self, endpoint: str, payload: dict) -> Optional[dict]:
        """POST to the API and return JSON response, or None on failure."""
        try:
            url = f'{self.api_url}{endpoint}'
            response = self.session.post(url, json=payload, timeout=15)
            if response.status_code in (200, 201):
                return response.json()
            else:
                print(f"[WebPublisher] Failed {endpoint}: HTTP {response.status_code}")
                try:
                    print(f"   Response: {response.text[:300]}")
                except Exception:
                    pass
                return None
        except requests.exceptions.ConnectionError:
            print(f"[WebPublisher] API not reachable at {self.api_url} — skipping")
            return None
        except Exception as e:
            print(f"[WebPublisher] Error posting to {endpoint}: {e}")
            return None

    def publish_thread(self, thread_data: Dict[str, Any],
                       tickers: List[str] = None,
                       sector: str = 'global',
                       image_url: Optional[str] = None,
                       market_snapshot: Optional[dict] = None,
                       source_file: Optional[str] = None) -> Optional[dict]:
        """
        Publish an X thread to the web API.

        Args:
            thread_data: Dict with 'tweets', 'tweet_count', 'copy_paste_ready'
            tickers: Asset tickers covered in the thread
            sector: Sector classification
            image_url: Lead image URL
            market_snapshot: Market data at generation time
            source_file: Path to the saved thread file

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        payload = {
            'tweets': thread_data.get('tweets', []),
            'tweet_count': thread_data.get('tweet_count', 0),
            'tickers': tickers or ['BTC', 'ETH'],
            'sector': sector,
            'image_url': image_url,
            'market_snapshot': market_snapshot,
            'source_file': source_file,
        }

        result = self._post('/api/content/publish/thread', payload)
        if result:
            print(f"[WebPublisher] Thread published: /post/{result.get('slug', '?')}")
        return result

    def publish_memo(self, ticker: str, memo: str,
                     current_price: Optional[float] = None,
                     sector: Optional[str] = None,
                     tickers: Optional[List[str]] = None,
                     image_url: Optional[str] = None,
                     market_snapshot: Optional[dict] = None,
                     source_file: Optional[str] = None) -> Optional[dict]:
        """
        Publish a market memo to the web API.

        Args:
            ticker: Asset ticker or sector name
            memo: Full memo body text
            current_price: Price at generation time
            sector: Sector classification
            tickers: List of tickers covered
            image_url: Lead image URL
            market_snapshot: Market data at generation time
            source_file: Path to the saved memo file

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        payload = {
            'ticker': ticker,
            'body': memo,
            'current_price': current_price,
            'sector': sector,
            'tickers': tickers or [ticker],
            'image_url': image_url,
            'market_snapshot': market_snapshot,
            'source_file': source_file,
        }

        result = self._post('/api/content/publish/memo', payload)
        if result:
            print(f"[WebPublisher] Memo published: /post/{result.get('slug', '?')}")
        return result

    def publish_article(self, title: str, body: str,
                        sector: str = 'global',
                        tickers: Optional[List[str]] = None,
                        image_url: Optional[str] = None,
                        market_snapshot: Optional[dict] = None,
                        source_file: Optional[str] = None) -> Optional[dict]:
        """
        Publish a long-form newsletter article to the web API (content_type='article').

        Args:
            title: Article headline
            body: Full article body (markdown)
            sector: Sector classification
            tickers: Asset tickers covered
            image_url: Lead image URL
            market_snapshot: Market data at generation time
            source_file: Path to saved article file

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        payload = {
            'title': title,
            'body': body,
            'sector': sector,
            'tickers': tickers or ['BTC', 'ETH'],
            'image_url': image_url,
            'market_snapshot': market_snapshot,
            'source_file': source_file,
        }

        result = self._post('/api/content/publish/article', payload)
        if result:
            print(f"[WebPublisher] Article published: /post/{result.get('slug', '?')}")
        return result

    def publish_news_tweet(self, ticker: str, tweet_text: str,
                           current_price: Optional[float] = None,
                           sector: Optional[str] = None,
                           tickers: Optional[List[str]] = None) -> Optional[dict]:
        """
        Publish a news tweet to the web API.

        Args:
            ticker: Asset ticker or sector name
            tweet_text: The news tweet body (max 280 chars)
            current_price: Price at generation time
            sector: Sector classification
            tickers: List of tickers covered

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        payload = {
            'ticker': ticker,
            'body': tweet_text,
            'current_price': current_price,
            'sector': sector,
            'tickers': tickers or [ticker],
        }

        result = self._post('/api/content/publish/news', payload)
        if result:
            print(f"[WebPublisher] News tweet published for {ticker}")
        return result

    def publish_market_snapshot(self, global_metrics: dict) -> Optional[dict]:
        """
        Publish a market snapshot for the dashboard.

        Args:
            global_metrics: Dict with btc_price, eth_price, total_market_cap, etc.

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        payload = {
            'btc_price': global_metrics.get('btc_price'),
            'eth_price': global_metrics.get('eth_price'),
            'total_market_cap': global_metrics.get('total_market_cap'),
            'btc_dominance': global_metrics.get('btc_dominance'),
            'fear_greed_index': global_metrics.get('fear_greed_index'),
            'fear_greed_label': global_metrics.get('fear_greed_classification'),
            'total_volume_24h': global_metrics.get('total_volume_24h'),
            'raw_data': global_metrics,
        }

        result = self._post('/api/market/snapshot', payload)
        if result:
            print(f"[WebPublisher] Market snapshot saved")
        return result

    def publish_asset_price(self, ticker: str, price_data: dict) -> Optional[dict]:
        """
        Publish a single asset price point.

        Args:
            ticker: Asset ticker
            price_data: Dict with price_usd, change_24h, volume_24h, market_cap, etc.

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        payload = {
            'ticker': ticker,
            'price_usd': price_data.get('price_usd', 0),
            'change_24h': price_data.get('price_change_24h'),
            'change_7d': price_data.get('price_change_7d'),
            'volume_24h': price_data.get('volume_24h'),
            'market_cap': price_data.get('market_cap'),
            'raw_data': price_data,
        }

        return self._post('/api/market/price', payload)

    def publish_regime(self, regime_data: dict) -> Optional[dict]:
        """
        Publish a regime detection result to the web API.

        Args:
            regime_data: Dict from RegimeDetector.detect_regime()

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        payload = {
            'regime_name': regime_data.get('regime', 'NEUTRAL'),
            'confidence': regime_data.get('confidence', 0.0),
            'description': regime_data.get('description'),
            'trader_action': regime_data.get('trader_action'),
            'expected_outcome': regime_data.get('expected_outcome'),
            'color': regime_data.get('color', 'zinc'),
            'supporting_signals': regime_data.get('supporting_signals'),
            'metrics_snapshot': regime_data.get('metrics_snapshot'),
            'historical_accuracy': regime_data.get('historical_accuracy'),
            'regime_count': regime_data.get('regime_count'),
            'previous_regime': regime_data.get('previous_regime'),
        }

        result = self._post('/api/intelligence/regime', payload)
        if result:
            print(f"[WebPublisher] Regime published: {regime_data.get('regime')} ({regime_data.get('confidence', 0) * 100:.0f}%)")
        return result

    def publish_metrics(self, metrics_dict: dict) -> Optional[dict]:
        """
        Publish metric data points for time-series storage.

        Args:
            metrics_dict: Dict of metric_name → value pairs from MarketMetrics

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        metrics = []
        for name, value in metrics_dict.items():
            if value is not None and isinstance(value, (int, float)):
                metrics.append({'metric_name': name, 'value': float(value)})

        if not metrics:
            return None

        payload = {'metrics': metrics}
        result = self._post('/api/intelligence/metrics', payload)
        if result:
            print(f"[WebPublisher] {result.get('saved', 0)} metrics saved to time-series")
        return result

    def publish_smart_money(self, scan_result: dict) -> Optional[dict]:
        """Publish smart money signals to the web API.

        Args:
            scan_result: Dict from SmartMoneyTracker.scan_signals()

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        signals = scan_result.get('signals', [])
        if not signals:
            return None

        payload = {
            'signals': signals,
            'net_sentiment': scan_result.get('net_sentiment', 'NEUTRAL'),
            'aggregate_interpretation': scan_result.get('aggregate_interpretation'),
        }

        result = self._post('/api/intelligence/smart-money', payload)
        if result:
            print(f"[WebPublisher] Smart money: {result.get('saved', 0)} signals ({result.get('net_sentiment', 'N/A')})")
        return result

    def publish_correlations(self, correlation_data: dict) -> Optional[dict]:
        """Publish a correlation matrix snapshot to the web API.

        Args:
            correlation_data: Dict from CorrelationEngine.calculate_correlations()

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        if not correlation_data.get('matrix'):
            return None

        payload = {
            'correlation_matrix': correlation_data.get('matrix', []),
            'labels': correlation_data.get('labels', []),
            'metric_keys': correlation_data.get('metric_keys', []),
            'strongest_pairs': correlation_data.get('strongest_pairs', []),
            'interpretation': correlation_data.get('interpretation'),
            'timeframe_hours': correlation_data.get('period_hours', 24),
            'data_points': correlation_data.get('data_points', 0),
        }

        result = self._post('/api/intelligence/correlations', payload)
        if result:
            n_pairs = len(correlation_data.get('strongest_pairs', []))
            print(f"[WebPublisher] Correlation matrix published ({n_pairs} strong pairs)")
        return result

    def publish_opportunities(self, scan_result: dict) -> Optional[dict]:
        """Publish opportunity scan results to the web API.

        Args:
            scan_result: Dict from OpportunityScanner.scan_opportunities()

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        if not scan_result.get('opportunities'):
            return None

        payload = {
            'opportunities': scan_result.get('opportunities', []),
            'opportunity_count': scan_result.get('opportunity_count', 0),
            'best_rr': scan_result.get('best_rr'),
            'highest_conviction': scan_result.get('highest_conviction'),
            'safest_play': scan_result.get('safest_play'),
            'regime': scan_result.get('regime'),
            'scanned_at': scan_result.get('scanned_at'),
        }

        result = self._post('/api/intelligence/opportunities', payload)
        if result:
            count = scan_result.get('opportunity_count', 0)
            print(f"[WebPublisher] Opportunities published: {count} ranked")
        return result

    def publish_trade_setup(self, setup_data: dict) -> Optional[dict]:
        """Publish an AI-generated trade setup to the web API.

        Args:
            setup_data: Dict from TradeSetupGenerator.generate_setup()

        Returns:
            API response dict or None on failure
        """
        if not self.enabled:
            return None

        if not setup_data:
            return None

        payload = {
            'asset': setup_data.get('asset', ''),
            'direction': setup_data.get('direction', 'LONG'),
            'setup_type': setup_data.get('setup_type'),
            'confidence': setup_data.get('confidence', 0.5),
            'entry_zones': setup_data.get('entry_zones', []),
            'stop_loss': setup_data.get('stop_loss'),
            'take_profits': setup_data.get('take_profits', []),
            'reasoning': setup_data.get('reasoning', []),
            'risk_factors': setup_data.get('risk_factors', []),
            'position_sizing': setup_data.get('position_sizing'),
            'regime_at_creation': setup_data.get('regime_at_creation'),
            'generated_at': setup_data.get('generated_at'),
        }

        result = self._post('/api/intelligence/setups', payload)
        if result:
            direction = setup_data.get('direction', '?')
            asset = setup_data.get('asset', '?')
            conf = setup_data.get('confidence', 0) * 100
            print(f"[WebPublisher] Trade setup published: {direction} {asset} ({conf:.0f}% confidence)")
        return result

    def verify_connection(self) -> bool:
        """Test connectivity to the API."""
        if not self.enabled:
            print("[WebPublisher] Not configured (WEB_API_URL not set)")
            return False
        try:
            response = self.session.get(f'{self.api_url}/api/health', timeout=5)
            if response.status_code == 200:
                print(f"[WebPublisher] Connected to API at {self.api_url}")
                return True
            else:
                print(f"[WebPublisher] API returned HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"[WebPublisher] Cannot reach API: {e}")
            return False

    def close(self):
        """Close the HTTP session."""
        self.session.close()
