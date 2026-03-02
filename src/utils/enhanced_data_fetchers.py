"""
Enhanced Data Fetchers with CoinMarketCap and Claude AI Content Writing

ARCHITECTURE NOTE (Updated):
- For DATA fetching: Use src.data.aggregator.DataAggregator
- For CONTENT writing: Use ClaudeResearchEngine._call_model()

This module provides:
1. CoinMarketCap integration (legacy - use DataAggregator instead)
2. ClaudeResearchEngine for content generation (threads, reports)

DEPRECATED:
- research_asset(), research_market_overview(), research_sector()
- AutomatedResearchLoop
These methods use Claude for DATA which wastes API tokens.
Use DataAggregator for data, Claude only for writing.
"""

import requests
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import anthropic


class CreditExhaustedError(Exception):
    """Raised when the Anthropic API key has no remaining credits.

    Callers should catch this specifically and halt content generation
    rather than posting a template fallback or error message publicly.
    """
import os
from bs4 import BeautifulSoup

from src.core.config import COINGECKO_API_KEY
from src.utils.helpers import get_current_timestamp


# =============================================================================
# COINMARKETCAP INTEGRATION (Replaces Alternative.me)
# =============================================================================

def get_global_crypto_metrics() -> Dict[str, Any]:
    """
    Get global crypto market metrics from multiple sources
    
    Returns:
        dict: {
            'total_market_cap': 3120000000000,
            'total_volume_24h': 156000000000,
            'btc_dominance': 58.5,
            'eth_dominance': 12.3,
            'market_cap_change_24h': -2.5,
            'active_cryptocurrencies': 28000,
            'fear_greed_equivalent': 24,
            'liquidation_volume_24h': 250000000,
            'open_interest_btc': 45000000000,
            'open_interest_eth': 15000000000,
            'btc_funding_rate': 0.00015,
            'eth_funding_rate': 0.00008
        }
    """
    
    # Try CoinMarketCap first
    try:
        url = "https://api.coinmarketcap.com/data-api/v3/global-metrics/quotes/latest"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        quote = data.get('data', {})
        total_market_cap = quote.get('quote', {}).get('USD', {}).get('total_market_cap', 0)
        
        if total_market_cap > 0:
            # Success with CoinMarketCap
            total_volume_24h = quote.get('quote', {}).get('USD', {}).get('total_volume_24h', 0)
            market_cap_change_24h = quote.get('quote', {}).get('USD', {}).get('total_market_cap_yesterday_percentage_change', 0)
            
            btc_dominance = quote.get('btc_dominance', 0)
            eth_dominance = quote.get('eth_dominance', 0)
            
            fear_greed = _calculate_fear_greed_from_metrics(
                market_cap_change_24h,
                btc_dominance,
                total_volume_24h / total_market_cap if total_market_cap > 0 else 0
            )
            
            # Fetch derivatives data from Binance
            derivatives_data = _get_binance_derivatives_data()
            
            return {
                'total_market_cap': total_market_cap,
                'total_volume_24h': total_volume_24h,
                'btc_dominance': btc_dominance,
                'eth_dominance': eth_dominance,
                'market_cap_change_24h': market_cap_change_24h,
                'active_cryptocurrencies': quote.get('active_cryptocurrencies', 0),
                'fear_greed_equivalent': fear_greed,
                'alt_season_index': _calculate_alt_season_index(btc_dominance),
                **derivatives_data,  # Add liquidation, open interest, funding rates
                'timestamp': get_current_timestamp(),
                'source': 'CoinMarketCap + Binance'
            }
    except Exception as e:
        print(f"⚠️  CoinMarketCap error: {e}")
    
    # Try CoinGecko as fallback
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        total_market_cap = data.get('total_market_cap', {}).get('usd', 0)
        total_volume_24h = data.get('total_volume', {}).get('usd', 0)
        market_cap_change = data.get('market_cap_change_percentage_24h_usd', 0)
        
        btc_dominance = data.get('btc_market_cap_percentage', 0)
        eth_dominance = data.get('eth_market_cap_percentage', 0)
        
        fear_greed = _calculate_fear_greed_from_metrics(
            market_cap_change,
            btc_dominance,
            total_volume_24h / total_market_cap if total_market_cap > 0 else 0
        )
        
        # Fetch derivatives data from Binance
        derivatives_data = _get_binance_derivatives_data()
        
        return {
            'total_market_cap': total_market_cap,
            'total_volume_24h': total_volume_24h,
            'btc_dominance': btc_dominance,
            'eth_dominance': eth_dominance,
            'market_cap_change_24h': market_cap_change,
            'active_cryptocurrencies': data.get('active_cryptocurrencies', 0),
            'fear_greed_equivalent': fear_greed,
            'alt_season_index': _calculate_alt_season_index(btc_dominance),
            **derivatives_data,  # Add liquidation, open interest, funding rates
            'timestamp': get_current_timestamp(),
            'source': 'CoinGecko + Binance'
        }
    except Exception as e:
        print(f"⚠️  CoinGecko error: {e}")
    
    # Return mock data as final fallback
    print("ℹ️  Using mock data for global metrics")
    return _get_mock_global_metrics()


def _calculate_fear_greed_from_metrics(mcap_change: float, btc_dom: float, velocity: float) -> int:
    """
    Calculate fear/greed index from market metrics
    
    Logic:
    - Negative market cap change = fear
    - High BTC dominance = fear (flight to safety)
    - Low velocity = fear (low activity)
    
    Returns:
        int: 0-100 (0 = extreme fear, 100 = extreme greed)
    """
    
    score = 50  # Start neutral
    
    # Market cap change impact (-10 to +10)
    if mcap_change < -5:
        score -= 20  # Extreme fear
    elif mcap_change < -2:
        score -= 10  # Fear
    elif mcap_change > 5:
        score += 20  # Extreme greed
    elif mcap_change > 2:
        score += 10  # Greed
    
    # BTC dominance impact
    if btc_dom > 60:
        score -= 10  # Fear (flight to BTC safety)
    elif btc_dom < 45:
        score += 10  # Greed (alt season)
    
    # Velocity impact
    if velocity < 0.05:
        score -= 10  # Fear (low activity)
    elif velocity > 0.15:
        score += 10  # Greed (high activity)
    
    # Clamp to 0-100
    return max(0, min(100, score))


def _calculate_alt_season_index(btc_dominance: float) -> int:
    """
    Calculate alt season index from BTC dominance
    
    Returns:
        int: 0-100 (0 = BTC season, 100 = alt season)
    """
    
    # Inverse relationship with BTC dominance
    # BTC dom 70% = Alt season index 0
    # BTC dom 40% = Alt season index 100
    
    return max(0, min(100, int((70 - btc_dominance) * 3.33)))


def _get_mock_global_metrics() -> Dict[str, Any]:
    """Fallback mock data with all metrics including derivatives"""
    return {
        'total_market_cap': 3120000000000,
        'total_volume_24h': 156000000000,
        'btc_dominance': 58.5,
        'eth_dominance': 12.3,
        'market_cap_change_24h': -2.5,
        'active_cryptocurrencies': 28000,
        'fear_greed_equivalent': 35,
        'alt_season_index': 30,
        'liquidation_volume_24h': 250000000,
        'open_interest_btc': 45000000000,
        'open_interest_eth': 15000000000,
        'btc_funding_rate': 0.00015,
        'eth_funding_rate': 0.00008,
        'timestamp': get_current_timestamp(),
        'source': 'Mock Data (Fallback)'
    }


def _get_binance_derivatives_data() -> Dict[str, Any]:
    """
    Fetch open interest, funding rates from Binance.
    Falls back to CoinGecko and Claude web search if Binance fails.

    Note: Liquidation endpoints (/fapi/v1/forceOrders requires API key,
    /fapi/v1/allForceOrders was removed by Binance). Liquidation data
    is fetched from CoinGlass or left as 0.
    """
    try:
        # Try Binance first (fastest, most reliable)
        print("📊 Fetching derivatives from Binance...")

        # Get BTC and ETH prices first (needed to convert OI from base to USD)
        price_url = "https://fapi.binance.com/fapi/v1/ticker/price"
        btc_price_r = requests.get(price_url, params={'symbol': 'BTCUSDT'}, timeout=5)
        eth_price_r = requests.get(price_url, params={'symbol': 'ETHUSDT'}, timeout=5)
        btc_price = float(btc_price_r.json().get('price', 0)) if btc_price_r.ok else 0
        eth_price = float(eth_price_r.json().get('price', 0)) if eth_price_r.ok else 0

        # Get open interest for BTC and ETH (returns base asset units, NOT USD)
        oi_url = "https://fapi.binance.com/fapi/v1/openInterest"
        btc_oi_response = requests.get(oi_url, params={'symbol': 'BTCUSDT'}, timeout=5)
        eth_oi_response = requests.get(oi_url, params={'symbol': 'ETHUSDT'}, timeout=5)

        btc_oi_base = float(btc_oi_response.json().get('openInterest', 0)) if btc_oi_response.ok else 0
        eth_oi_base = float(eth_oi_response.json().get('openInterest', 0)) if eth_oi_response.ok else 0

        # Convert OI to USD
        btc_oi_usd = btc_oi_base * btc_price
        eth_oi_usd = eth_oi_base * eth_price

        # Get latest funding rates
        funding_url = "https://fapi.binance.com/fapi/v1/fundingRate"
        btc_funding_response = requests.get(funding_url, params={'symbol': 'BTCUSDT', 'limit': 1}, timeout=5)
        eth_funding_response = requests.get(funding_url, params={'symbol': 'ETHUSDT', 'limit': 1}, timeout=5)

        btc_funding = float(btc_funding_response.json()[0].get('fundingRate', 0)) if btc_funding_response.ok and btc_funding_response.json() else 0
        eth_funding = float(eth_funding_response.json()[0].get('fundingRate', 0)) if eth_funding_response.ok and eth_funding_response.json() else 0

        # Try to get liquidation data from CoinGlass (free tier)
        liquidation_volume = 0
        try:
            cg_url = "https://open-api.coinglass.com/public/v2/liquidation_history"
            cg_r = requests.get(cg_url, params={'symbol': 'BTC', 'time_type': '1'}, timeout=5)
            if cg_r.ok:
                cg_data = cg_r.json()
                if cg_data.get('success') and cg_data.get('data'):
                    for entry in cg_data['data'][-1:]:  # Latest entry
                        liquidation_volume = float(entry.get('longVolUsd', 0)) + float(entry.get('shortVolUsd', 0))
        except Exception:
            pass  # Liquidation data is supplementary, don't fail on it

        if btc_oi_usd > 0:
            print(f"   ✅ Binance data: Liquidation=${liquidation_volume/1e6:.2f}M, BTC OI=${btc_oi_usd/1e9:.2f}B, ETH OI=${eth_oi_usd/1e9:.2f}B")
            return {
                'liquidation_volume_24h': liquidation_volume,
                'open_interest_btc': btc_oi_usd,
                'open_interest_eth': eth_oi_usd,
                'btc_funding_rate': btc_funding,
                'eth_funding_rate': eth_funding,
                'source': 'Binance Futures'
            }
    except Exception as e:
        print(f"⚠️  Binance derivatives error: {e}")
    
    # Fallback to CoinGecko
    try:
        print("📊 Fetching derivatives from CoinGecko...")
        url = "https://api.coingecko.com/api/v3/derivatives"
        response = requests.get(url, timeout=5)
        
        if response.ok:
            data = response.json()
            
            # Parse CoinGecko derivatives data
            total_liquidation = 0
            btc_oi = 0
            eth_oi = 0
            
            for exchange in data:
                if exchange.get('name') == 'Binance':
                    total_liquidation += float(exchange.get('liquidation_volume_24h', 0) or 0)
                    btc_oi += float(exchange.get('open_interest_btc', 0) or 0)
                    eth_oi += float(exchange.get('open_interest_eth', 0) or 0)
            
            if total_liquidation > 0 or btc_oi > 0:
                print(f"   ✅ CoinGecko data: Liquidation=${total_liquidation/1e6:.2f}M, BTC OI=${btc_oi/1e9:.2f}B")
                return {
                    'liquidation_volume_24h': total_liquidation,
                    'open_interest_btc': btc_oi,
                    'open_interest_eth': eth_oi,
                    'btc_funding_rate': 0.00015,
                    'eth_funding_rate': 0.00008,
                    'source': 'CoinGecko Derivatives'
                }
    except Exception as e:
        print(f"⚠️  CoinGecko derivatives error: {e}")
    
    # Fallback to Claude web search for derivatives data
    try:
        print("📊 Searching web for derivatives data via Claude...")
        from src.utils.enhanced_data_fetchers import ClaudeResearchEngine
        
        engine = ClaudeResearchEngine(os.getenv('ANTHROPIC_API_KEY'))
        
        prompt = """Search the web for current crypto derivatives metrics and return ONLY JSON with these fields:
        {
            "liquidation_volume_24h": <number in USD>,
            "open_interest_btc": <number in USD>,
            "open_interest_eth": <number in USD>,
            "btc_funding_rate": <decimal>,
            "eth_funding_rate": <decimal>
        }
        Return ONLY valid JSON, no other text."""
        
        try:
            response = engine._call_model(prompt, max_tokens=500)
            result_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    result_text += block.text
            
            # Extract JSON from response
            import json as json_lib
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                data = json_lib.loads(json_str)
                print(f"   ✅ Claude web search: Found derivatives data")
                return data
        except:
            pass
    except Exception as e:
        print(f"⚠️  Claude web search error: {e}")
    
    # Final fallback - reasonable defaults
    print("ℹ️  Using default derivatives data")
    return {
        'liquidation_volume_24h': 250000000,
        'open_interest_btc': 45000000000,
        'open_interest_eth': 15000000000,
        'btc_funding_rate': 0.00015,
        'eth_funding_rate': 0.00008,
        'source': 'Default Values'
    }


# =============================================================================
# CLAUDE AI RESEARCH ENGINE
# =============================================================================

class ClaudeResearchEngine:
    """
    Claude AI Content Writing Engine

    IMPORTANT: Use this class ONLY for content generation (threads, reports).
    For DATA fetching, use src.data.aggregator.DataAggregator instead.

    Correct Usage:
        engine = ClaudeResearchEngine(api_key)
        response = engine._call_model("Write a tweet about BTC at $78,000")

    DEPRECATED methods (do not use for new code):
        - research_asset() - use DataAggregator.get_price() instead
        - research_market_overview() - use DataAggregator.get_global_metrics() instead
        - research_sector() - use DataAggregator.get_defi_metrics() instead
    """
    
    def __init__(self, api_key: str, backup_api_keys: Dict[str, str] = None, model: str = None):
        """Initialize Claude client with backup API keys
        
        Args:
            api_key: Anthropic API key
            backup_api_keys: Optional dict with backup API keys:
                {'coingecko': key, 'glassnode': key, 'cryptopanic': key, 'etherscan': key}
        """
        if not api_key:
            self.client = None
            self.api_available = False
        else:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.api_available = True
        # Allow overriding model via constructor arg, env var, or default
        self.model = model or os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-5-20250929')
        # Fallback models to try if the requested model is not available to the account
        self.fallback_models = [
            'claude-sonnet-4-5-20250929',
            'claude-sonnet-4-20250514',
        ]
        
        # Backup API keys for when scraping fails
        self.backup_keys = backup_api_keys or {}
        self.coingecko_key = self.backup_keys.get('coingecko', COINGECKO_API_KEY)
        self.glassnode_key = self.backup_keys.get('glassnode', '')
        self.cryptopanic_key = self.backup_keys.get('cryptopanic', 'demo')  # Use demo if no key
        self.etherscan_key = self.backup_keys.get('etherscan', '')

    def _call_model(self, prompt: str, max_tokens: int = 1000):
        """Call Anthropic messages.create with model fallback and retry logic."""
        import time
        
        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        last_err = None
        
        for model_name in models_to_try:
            # Retry up to 3 times with exponential backoff for overload/rate limit errors
            for attempt in range(3):
                try:
                    response = self.client.messages.create(
                        model=model_name,
                        max_tokens=max_tokens,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    # Update active model to the working one
                    self.model = model_name
                    return response
                    
                except anthropic.NotFoundError as nf:
                    print(f"Model not found: {model_name}, trying next fallback...")
                    last_err = nf
                    break  # Don't retry, try next model
                    
                except (anthropic.APIStatusError, anthropic.APIError) as ae:
                    error_msg = str(ae).lower()
                    status = getattr(ae, 'status_code', None)

                    # Billing / credit exhaustion — do NOT retry, raise immediately
                    if (status in (402, 403) or
                            any(kw in error_msg for kw in
                                ('credit', 'billing', 'insufficient_credits',
                                 'payment', 'quota', 'out of credits'))):
                        raise CreditExhaustedError(
                            f"Anthropic API credits exhausted (HTTP {status}): {ae}"
                        ) from ae

                    if "overload" in error_msg or "529" in error_msg:
                        wait_time = 2 ** attempt  # 1s, 2s, 4s
                        print(f"API overloaded (attempt {attempt+1}/3), waiting {wait_time}s...")
                        time.sleep(wait_time)
                        last_err = ae
                        continue

                    elif "rate" in error_msg or "429" in error_msg:
                        wait_time = 3 ** attempt  # 1s, 3s, 9s
                        print(f"Rate limited (attempt {attempt+1}/3), waiting {wait_time}s...")
                        time.sleep(wait_time)
                        last_err = ae
                        continue

                    else:
                        last_err = ae
                        break
                    
                except Exception as e:
                    # Non-retryable errors - try next model
                    last_err = e
                    break

        # If we exhausted models or encountered an error, raise the last error
        if last_err:
            raise last_err
    
    def _scrape_asset_data(self, ticker: str) -> str:
        """
        Scrape current data for an asset from multiple sources as backup
        
        Sources:
        - CoinMarketCap (primary)
        - CoinGecko (backup)
        - Glassnode (on-chain data)
        - CryptoPanic (news)
        - Etherscan (ETH-specific)
        
        Returns:
            str: Raw data from web scraping
        """
        data_parts = []
        
        try:
            # CoinMarketCap (primary source)
            cmc_url = f"https://coinmarketcap.com/currencies/{ticker.lower()}/"
            response = requests.get(cmc_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                data_parts.append(f"CoinMarketCap data: {soup.get_text()[:2000]}...")
        except Exception as e:
            data_parts.append(f"CoinMarketCap error: {e}")
        
        try:
            # CoinGecko (backup market data)
            cg_url = f"https://www.coingecko.com/en/coins/{ticker.lower()}"
            response = requests.get(cg_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                data_parts.append(f"CoinGecko data: {soup.get_text()[:2000]}...")
        except Exception as e:
            data_parts.append(f"CoinGecko error: {e}")
        
        try:
            # Glassnode (on-chain metrics) - use free alternative sources
            if ticker.upper() == 'BTC':
                # Use Blockchain.com API for BTC on-chain data
                btc_url = "https://api.blockchain.info/stats"
                response = requests.get(btc_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    data_parts.append(f"Blockchain.com BTC on-chain: {data}")
                else:
                    data_parts.append(f"Blockchain.com BTC on-chain: API unavailable")
            elif ticker.upper() == 'ETH':
                # Use Etherscan free tier for ETH data
                if self.etherscan_key:
                    eth_url = f"https://api.etherscan.io/api?module=stats&action=ethsupply&apikey={self.etherscan_key}"
                    response = requests.get(eth_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        data_parts.append(f"Etherscan ETH on-chain: {data}")
                else:
                    data_parts.append(f"Etherscan ETH on-chain: API key required for detailed data")
            else:
                # For other assets, use general market data
                data_parts.append(f"On-chain data: Limited free sources for {ticker}")
        except Exception as e:
            data_parts.append(f"On-chain error: {e}")
        
        try:
            # CryptoPanic (news and sentiment) - use API key if available
            if self.cryptopanic_key and self.cryptopanic_key != 'demo':
                cp_url = f"https://cryptopanic.com/api/v3/posts/?auth_token={self.cryptopanic_key}&currencies={ticker.lower()}"
            else:
                cp_url = f"https://cryptopanic.com/api/v3/posts/?auth_token=demo&currencies={ticker.lower()}"
            response = requests.get(cp_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                data_parts.append(f"CryptoPanic news: {str(data)[:1500]}...")
            else:
                data_parts.append(f"CryptoPanic news: API returned status {response.status_code}")
        except Exception as e:
            data_parts.append(f"CryptoPanic error: {e}")
            # Etherscan (ETH-specific data) - use API key if available
            if ticker.upper() == 'ETH' and self.etherscan_key:
                eth_url = f"https://api.etherscan.io/api?module=stats&action=ethsupply&apikey={self.etherscan_key}"
                response = requests.get(eth_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    data_parts.append(f"Etherscan API: {data}")
            elif ticker.upper() == 'ETH':
                # Fallback to web scraping
                eth_url = "https://etherscan.io/"
                response = requests.get(eth_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    data_parts.append(f"Etherscan data: {soup.get_text()[:1500]}...")
        except Exception as e:
            data_parts.append(f"Etherscan error: {e}")
        
        return "\n\n".join(data_parts) if data_parts else f"No web data available for {ticker}"
    
    def _scrape_market_data(self) -> str:
        """
        Scrape current market data from multiple sources as backup
        
        Sources:
        - CoinMarketCap (primary)
        - Alternative.me (fear/greed)
        - Glassnode (market on-chain)
        - CryptoPanic (market news)
        
        Returns:
            str: Raw market data from web scraping
        """
        data_parts = []
        
        try:
            # CoinMarketCap global (primary)
            cmc_url = "https://coinmarketcap.com/"
            response = requests.get(cmc_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                data_parts.append(f"CoinMarketCap global: {soup.get_text()[:3000]}...")
        except Exception as e:
            data_parts.append(f"CoinMarketCap global error: {e}")
        
        try:
            # Alternative.me fear/greed (backup sentiment)
            fear_url = "https://api.alternative.me/fng/"
            response = requests.get(fear_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                data_parts.append(f"Fear/Greed Index: {data}")
        except Exception as e:
            data_parts.append(f"Fear/Greed error: {e}")
        
        try:
            # Glassnode market overview - use free alternative
            # Use CoinMarketCap's free global metrics as Glassnode alternative
            cmc_global_url = "https://api.coinmarketcap.com/data-api/v3/global-metrics/quotes/latest"
            response = requests.get(cmc_global_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                data_parts.append(f"Global market metrics: {data}")
            else:
                data_parts.append(f"Global market metrics: API unavailable")
        except Exception as e:
            data_parts.append(f"Global market error: {e}")
        
        try:
            # CryptoPanic market news - use API key if available
            if self.cryptopanic_key and self.cryptopanic_key != 'demo':
                cp_url = f"https://cryptopanic.com/api/v3/posts/?auth_token={self.cryptopanic_key}&kind=news"
            else:
                cp_url = "https://cryptopanic.com/api/v3/posts/?auth_token=demo&kind=news"
            response = requests.get(cp_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                data_parts.append(f"CryptoPanic market news: {data}")
        except Exception as e:
            data_parts.append(f"CryptoPanic market error: {e}")
        
        return "\n\n".join(data_parts) if data_parts else "No market data available"
    
    def _scrape_sector_data(self, sector: str) -> str:
        """
        Scrape sector-specific data from multiple sources as backup
        
        Sources:
        - CoinMarketCap (primary)
        - Glassnode (on-chain sector data)
        - CryptoPanic (sector news)
        - CoinGecko (sector trends)
        
        Returns:
            str: Raw sector data from web scraping
        """
        data_parts = []
        
        # Map sectors to CoinMarketCap categories
        sector_mapping = {
            'memecoins': 'meme-token',
            'defi': 'decentralized-finance-defi',
            'privacy': 'privacy-coins',
            'layer1': 'layer-1',
        }
        
        category = sector_mapping.get(sector, sector)
        
        try:
            # CoinMarketCap category page (primary)
            cmc_url = f"https://coinmarketcap.com/view/{category}/"
            response = requests.get(cmc_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                data_parts.append(f"CoinMarketCap {sector}: {soup.get_text()[:3000]}...")
        except Exception as e:
            data_parts.append(f"CoinMarketCap {sector} error: {e}")
        
        try:
            # Glassnode sector data (on-chain metrics) - use free alternatives
            if sector == 'defi':
                # Use DeFi Pulse or similar free API
                defi_url = "https://api.llama.fi/protocol/tvl"
                response = requests.get(defi_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    data_parts.append(f"DeFi TVL data: {str(data)[:1500]}...")
                else:
                    data_parts.append(f"DeFi TVL data: API unavailable")
            elif sector == 'privacy':
                # Use general market data for privacy coins
                data_parts.append(f"Privacy sector: Using general market data sources")
            else:
                # For other sectors, use general market data
                data_parts.append(f"{sector.title()} sector: Using general market data sources")
        except Exception as e:
            data_parts.append(f"Sector on-chain error: {e}")
        
        try:
            # CryptoPanic sector news - use API key if available
            if self.cryptopanic_key and self.cryptopanic_key != 'demo':
                cp_url = f"https://cryptopanic.com/api/v3/posts/?auth_token={self.cryptopanic_key}&kind=news&currencies={sector}"
            else:
                cp_url = f"https://cryptopanic.com/api/v3/posts/?auth_token=demo&kind=news&currencies={sector}"
            response = requests.get(cp_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                data_parts.append(f"CryptoPanic {sector} news: {data}")
        except Exception as e:
            data_parts.append(f"CryptoPanic {sector} error: {e}")
        
        try:
            # CoinGecko sector trends
            cg_url = f"https://www.coingecko.com/en/categories/{category.replace('-', '-')}"
            response = requests.get(cg_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                data_parts.append(f"CoinGecko {sector}: {soup.get_text()[:2000]}...")
        except Exception as e:
            data_parts.append(f"CoinGecko {sector} error: {e}")
        
        return "\n\n".join(data_parts) if data_parts else f"No {sector} sector data available"
    
    def _get_mock_asset_research(self, ticker: str) -> Dict[str, Any]:
        """Mock research data when API is not available"""
        return {
            'ticker': ticker,
            'price_usd': 45000 if ticker == 'BTC' else 2400 if ticker == 'ETH' else 1.23,
            'price_change_24h': 2.5,
            'volume_24h': 28000000000,
            'market_cap': 850000000000,
            'sentiment': 'bullish',
            'news_summary': f'Recent developments in {ticker} market',
            'on_chain_activity': f'Network activity for {ticker}',
            'risk_factors': [f'Market volatility for {ticker}'],
            'key_developments': [f'Key development for {ticker}'],
            'timestamp': get_current_timestamp(),
            'note': 'Mock data - set ANTHROPIC_API_KEY for real Claude AI research'
        }
    
    def _get_mock_market_research(self) -> Dict[str, Any]:
        """Mock market research data when API is not available"""
        return {
            'market_cap_total': 2500000000000,
            'market_change_24h': -1.2,
            'btc_dominance': 58.5,
            'eth_dominance': 12.3,
            'fear_greed_index': 45,
            'btc_price': 45000,
            'btc_change_24h': 2.1,
            'eth_price': 2400,
            'eth_change_24h': -0.5,
            'trending_sectors': ['memecoins', 'DeFi'],
            'top_news': ['Market update 1', 'Market update 2'],
            'sentiment': 'neutral',
            'risk_factors': ['Market volatility', 'Regulatory concerns'],
            'timestamp': get_current_timestamp(),
            'note': 'Mock data - set ANTHROPIC_API_KEY for real Claude AI research'
        }
    
    def research_asset(self, ticker: str) -> Dict[str, Any]:
        """
        DEPRECATED: Use DataAggregator.get_price() and DataAggregator.get_asset_data() instead.

        This method wastes Claude API tokens on data fetching.
        Use: from src.data.aggregator import DataAggregator
             agg = DataAggregator()
             price = agg.get_price(ticker)

        Args:
            ticker: Asset symbol (e.g., 'BTC', 'ETH')

        Returns:
            dict: Comprehensive research results
        """
        import warnings
        warnings.warn(
            "research_asset() is deprecated. Use DataAggregator.get_price() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # First, scrape current data from CoinMarketCap and other sources
        raw_data = self._scrape_asset_data(ticker)
        
        # Then analyze with Claude
        prompt = f"""Analyze this cryptocurrency data for {ticker} and provide structured insights.

RAW DATA FROM WEB SCRAPING:
{raw_data}

Based on this data, provide analysis in this exact JSON format:
{{
    "ticker": "{ticker}",
    "price_usd": 45000,
    "price_change_24h": 2.5,
    "volume_24h": 28000000000,
    "market_cap": 850000000000,
    "sentiment": "bullish|bearish|neutral",
    "news_summary": "Brief summary of recent news",
    "on_chain_activity": "Summary of network activity",
    "risk_factors": ["Risk 1", "Risk 2"],
    "key_developments": ["Development 1", "Development 2"],
    "timestamp": "{get_current_timestamp()}"
}}

Focus on FACTUAL information only. Use the scraped data provided."""

        try:
            if not self.api_available or not self.client:
                return self._get_mock_asset_research(ticker)
            
            response = self._call_model(prompt, max_tokens=4000)
            
            # Extract text from response
            result_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    result_text += block.text
            
            # Try to parse as JSON, fall back to structured text
            try:
                return json.loads(result_text)
            except:
                return {
                    'ticker': ticker,
                    'research_text': result_text,
                    'timestamp': get_current_timestamp()
                }
                
        except Exception as e:
            print(f"❌ Claude research error for {ticker}: {e}")
            return self._get_mock_asset_research(ticker)
    
    def research_market_overview(self) -> Dict[str, Any]:
        """
        DEPRECATED: Use DataAggregator.get_global_metrics() instead.

        This method wastes Claude API tokens on data fetching.
        Use: from src.data.aggregator import DataAggregator
             agg = DataAggregator()
             metrics = agg.get_global_metrics()

        Returns:
            dict: Comprehensive market overview
        """
        import warnings
        warnings.warn(
            "research_market_overview() is deprecated. Use DataAggregator.get_global_metrics() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # Scrape market data
        raw_data = self._scrape_market_data()
        
        # Analyze with Claude
        prompt = f"""Analyze this cryptocurrency market data and provide structured market overview.

RAW MARKET DATA FROM WEB SCRAPING:
{raw_data}

Based on this data, provide analysis in this exact JSON format:
{{
    "market_cap_total": 2500000000000,
    "market_change_24h": -1.2,
    "btc_dominance": 58.5,
    "eth_dominance": 12.3,
    "fear_greed_index": 45,
    "btc_price": 45000,
    "btc_change_24h": 2.1,
    "eth_price": 2400,
    "eth_change_24h": -0.5,
    "trending_sectors": ["memecoins", "DeFi"],
    "top_news": ["News item 1", "News item 2"],
    "sentiment": "neutral",
    "risk_factors": ["Risk 1", "Risk 2"],
    "timestamp": "{get_current_timestamp()}"
}}

Focus on FACTUAL information from the scraped data."""

        try:
            if not self.api_available or not self.client:
                return self._get_mock_market_research()
            
            response = self._call_model(prompt, max_tokens=4000)
            
            result_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    result_text += block.text
            
            try:
                return json.loads(result_text)
            except:
                return {
                    'research_text': result_text,
                    'timestamp': get_current_timestamp()
                }
                
        except Exception as e:
            print(f"❌ Claude market research error: {e}")
            return self._get_mock_market_research()
    
    def research_sector(self, sector: str, top_assets: int = 5) -> Dict[str, Any]:
        """
        DEPRECATED: Use DataAggregator.get_defi_metrics() or pillar analyzers instead.

        This method wastes Claude API tokens on data fetching.
        Use: from src.data.aggregator import DataAggregator
             agg = DataAggregator()
             defi = agg.get_defi_metrics(ticker)

        Args:
            sector: 'memecoins', 'defi', 'privacy', 'layer1', etc.
            top_assets: Number of top assets to analyze

        Returns:
            dict: Sector research results
        """
        import warnings
        warnings.warn(
            "research_sector() is deprecated. Use DataAggregator or pillar analyzers instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Scrape sector data
        raw_data = self._scrape_sector_data(sector)
        
        # Analyze with Claude
        prompt = f"""Analyze this {sector} sector data and provide structured sector analysis.

RAW SECTOR DATA FROM WEB SCRAPING:
{raw_data}

Based on this data, provide analysis in this exact JSON format:
{{
    "sector": "{sector}",
    "market_cap": 50000000000,
    "change_24h": 3.2,
    "top_assets": [
        {{"name": "Asset1", "ticker": "TICK1", "price": 1.23, "change_24h": 5.6}},
        {{"name": "Asset2", "ticker": "TICK2", "price": 4.56, "change_24h": -2.1}}
    ],
    "trends": ["Trend 1", "Trend 2"],
    "sentiment": "bullish",
    "risks": ["Risk 1", "Risk 2"],
    "opportunities": ["Opp 1", "Opp 2"],
    "timestamp": "{get_current_timestamp()}"
}}

Focus on FACTUAL information from the scraped data. Analyze top {top_assets} assets."""

        try:
            if not self.api_available or not self.client:
                return self._get_mock_sector_research(sector, top_assets)
            
            response = self._call_model(prompt, max_tokens=4000)
            
            result_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    result_text += block.text
            
            try:
                return json.loads(result_text)
            except:
                return {
                    'sector': sector,
                    'research_text': result_text,
                    'timestamp': get_current_timestamp()
                }
                
        except Exception as e:
            print(f"❌ Claude sector research error: {e}")
            return self._get_mock_sector_research(sector, top_assets)


    def _get_mock_sector_research(self, sector: str, top_assets: int) -> Dict[str, Any]:
        """Mock sector research data when API is not available"""
        mock_assets = [
            {'name': f'{sector.title()} Asset 1', 'ticker': f'{sector.upper()}1', 'price': 1.23, 'change_24h': 5.6},
            {'name': f'{sector.title()} Asset 2', 'ticker': f'{sector.upper()}2', 'price': 4.56, 'change_24h': -2.1},
            {'name': f'{sector.title()} Asset 3', 'ticker': f'{sector.upper()}3', 'price': 0.89, 'change_24h': 12.3},
        ][:top_assets]
        
        return {
            'sector': sector,
            'market_cap': 50000000000,
            'change_24h': 3.2,
            'top_assets': mock_assets,
            'trends': [f'{sector.title()} trend 1', f'{sector.title()} trend 2'],
            'sentiment': 'bullish',
            'risks': [f'{sector.title()} risk 1', f'{sector.title()} risk 2'],
            'opportunities': [f'{sector.title()} opportunity 1', f'{sector.title()} opportunity 2'],
            'timestamp': get_current_timestamp(),
            'note': 'Mock data - set ANTHROPIC_API_KEY for real Claude AI research'
        }


# =============================================================================
# AUTOMATED RESEARCH LOOP (DEPRECATED)
# =============================================================================

class AutomatedResearchLoop:
    """
    DEPRECATED: Do not use this class.

    This class uses Claude for DATA fetching which wastes API tokens.
    The main orchestrator (main.py) now uses DataAggregator for data
    and only uses Claude for content writing.

    For the new approach, see main.py:CryptoAnalysisOrchestrator
    """
    
    def __init__(self, claude_api_key: str, interval_seconds: int = 60, backup_api_keys: Dict[str, str] = None):
        """
        Initialize research loop
        
        Args:
            claude_api_key: Anthropic API key
            interval_seconds: Research interval (default 60s)
            backup_api_keys: Optional dict with backup API keys for fallback sources
        """
        self.research_engine = ClaudeResearchEngine(claude_api_key, backup_api_keys)
        self.interval = interval_seconds
        self.running = False
        self.latest_research = {}
    
    def start(self):
        """Start the research loop"""
        self.running = True
        print(f"🔄 Starting automated research loop (every {self.interval}s)")
        
        while self.running:
            try:
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Running research cycle...")
                
                # 1. Market overview
                print("   📊 Researching market overview...")
                market = self.research_engine.research_market_overview()
                self.latest_research['market'] = market
                
                # 2. BTC
                print("   ₿ Researching BTC...")
                btc = self.research_engine.research_asset('BTC')
                self.latest_research['BTC'] = btc
                
                # 3. ETH
                print("   ⟠ Researching ETH...")
                eth = self.research_engine.research_asset('ETH')
                self.latest_research['ETH'] = eth
                
                # 4. Trending sector (rotate)
                sectors = ['memecoins', 'defi', 'privacy']
                sector = sectors[int(time.time() / 180) % len(sectors)]  # Rotate every 3 minutes
                print(f"   🔥 Researching {sector}...")
                sector_data = self.research_engine.research_sector(sector)
                self.latest_research[sector] = sector_data
                
                # Save to file
                self._save_research()
                
                print(f"   ✅ Research complete. Next update in {self.interval}s")
                
                # Wait for next cycle
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                print("\n⏹️  Stopping research loop...")
                self.running = False
                break
            except Exception as e:
                print(f"   ❌ Error in research cycle: {e}")
                time.sleep(self.interval)
    
    def stop(self):
        """Stop the research loop"""
        self.running = False
    
    def get_latest_research(self) -> Dict[str, Any]:
        """Get the latest research results"""
        return self.latest_research
    
    def _save_research(self):
        """Save research to timestamped file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"research_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.latest_research, f, indent=2)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("ENHANCED DATA FETCHERS - TEST")
    print("=" * 80)
    
    # 1. Test CoinMarketCap
    print("\n1. Testing CoinMarketCap global metrics...")
    metrics = get_global_crypto_metrics()
    print(f"   Total Market Cap: ${metrics['total_market_cap']/1e12:.2f}T")
    print(f"   BTC Dominance: {metrics['btc_dominance']:.1f}%")
    print(f"   Fear/Greed Equivalent: {metrics['fear_greed_equivalent']}")
    print(f"   Alt Season Index: {metrics['alt_season_index']}")
    
    # 2. Test Claude Research (requires API key)
    print("\n2. Claude AI Research Engine:")
    print("   Set ANTHROPIC_API_KEY environment variable to test")
    print("   Example:")
    print("     export ANTHROPIC_API_KEY='your-key-here'")
    print("     python -c 'from src.utils.enhanced_data_fetchers import ClaudeResearchEngine; ...")
    
    print("\n✅ Tests complete!")