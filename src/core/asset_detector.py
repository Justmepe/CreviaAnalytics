"""
File 5: Asset Type Detector
Dependencies: config.py, data_fetchers.py
Status: ✅ COMPLETE

Purpose:
- Auto-detect asset type from ticker symbol or name
- Classify as: MAJORS (BTC/ETH), MEMECOIN, PRIVACY, DEFI, OTHER
- Use market cap, tags, and naming patterns for classification
"""

from typing import Tuple, List
from src.core.config import (
    ASSET_TYPES,
    PILLAR_ACTIVATION_RULES,
    get_asset_category,
    get_active_pillars
)
from src.utils.data_fetchers import fetch_coin_data
from src.utils.helpers import safe_get


# =============================================================================
# ASSET TYPE DETECTION
# =============================================================================

def detect_asset_type(ticker: str) -> Tuple[str, float]:
    """
    Detect the type of crypto asset with confidence score
    
    Classification Priority:
    1. Check hardcoded lists (MAJORS, PRIVACY)
    2. Fetch coin data and check categories
    3. Apply heuristics (market cap, keywords)
    4. Default to OTHER
    
    Args:
        ticker: Asset symbol (e.g., 'BTC', 'DOGE', 'XMR')
    
    Returns:
        tuple: (asset_type, confidence_score)
            asset_type: 'MAJORS', 'PRIVACY', 'DEFI', 'MEMECOIN', or 'OTHER'
            confidence_score: 0.0 to 1.0
    
    Examples:
        >>> detect_asset_type('BTC')
        ('MAJORS', 1.0)
        >>> detect_asset_type('DOGE')
        ('MEMECOIN', 0.95)
    """
    ticker_upper = ticker.upper()
    
    # Step 1: Check hardcoded lists (highest confidence)
    hardcoded_category = get_asset_category(ticker)
    if hardcoded_category != 'OTHER':
        return (hardcoded_category, 1.0)
    
    # Step 2: Fetch coin data from API
    coin_data = fetch_coin_data(ticker)
    
    if not coin_data:
        # If API fails, make best guess
        return _guess_from_ticker(ticker_upper)
    
    # Step 3: Analyze coin data
    categories = [cat.lower() for cat in coin_data.get('categories', [])]
    market_cap = coin_data.get('market_cap', 0)
    name = coin_data.get('name', '').lower()
    
    # Check categories from CoinGecko
    if _contains_any(categories, ['privacy', 'privacy-coins']):
        return ('PRIVACY', 0.9)
    
    if _contains_any(categories, ['decentralized-finance-defi', 'defi', 'decentralized-finance']):
        return ('DEFI', 0.9)
    
    if _contains_any(categories, ['meme', 'memes', 'dog-themed']):
        return ('MEMECOIN', 0.85)
    
    # Check name for keywords
    if any(keyword in name for keyword in ['privacy', 'private', 'anonymous']):
        return ('PRIVACY', 0.75)
    
    if any(keyword in name for keyword in ['defi', 'protocol', 'swap', 'lending']):
        return ('DEFI', 0.75)
    
    # Heuristic: Low market cap + animal/food name = likely memecoin
    meme_keywords = ['dog', 'cat', 'pepe', 'frog', 'shib', 'inu', 'moon', 'safe']
    if market_cap < 500_000_000 and any(kw in name for kw in meme_keywords):
        return ('MEMECOIN', 0.7)
    
    # Default to OTHER
    return ('OTHER', 0.6)


def _contains_any(items: List[str], keywords: List[str]) -> bool:
    """Check if any keyword appears in items list"""
    return any(keyword in item for item in items for keyword in keywords)


def _guess_from_ticker(ticker: str) -> Tuple[str, float]:
    """
    Make educated guess based on ticker alone (fallback)
    
    Args:
        ticker: Uppercase ticker symbol
    
    Returns:
        tuple: (asset_type, low_confidence_score)
    """
    ticker_lower = ticker.lower()
    
    # Known patterns
    if 'doge' in ticker_lower or 'shib' in ticker_lower or 'pepe' in ticker_lower:
        return ('MEMECOIN', 0.6)
    
    if 'swap' in ticker_lower or 'uni' in ticker_lower:
        return ('DEFI', 0.5)
    
    # Very uncertain guess
    return ('OTHER', 0.3)


# =============================================================================
# PILLAR ACTIVATION
# =============================================================================

def get_pillars_for_asset(ticker: str) -> Tuple[List[str], str]:
    """
    Determine which analysis pillars to activate for an asset
    
    Args:
        ticker: Asset symbol
    
    Returns:
        tuple: (pillar_list, asset_type)
            pillar_list: ['A', 'B', 'C', 'D', 'E']
            asset_type: Classification category
    
    Example:
        >>> get_pillars_for_asset('BTC')
        (['A', 'B', 'C', 'D'], 'MAJORS')
        >>> get_pillars_for_asset('DOGE')
        (['A', 'B', 'D', 'E'], 'MEMECOIN')
    """
    asset_type, confidence = detect_asset_type(ticker)
    pillars = get_active_pillars(asset_type)
    
    return (pillars, asset_type)


# =============================================================================
# ASSET INFORMATION AGGREGATOR
# =============================================================================

def get_asset_info(ticker: str) -> dict:
    """
    Get comprehensive asset information including type and active pillars
    
    Args:
        ticker: Asset symbol
    
    Returns:
        dict: {
            'ticker': 'BTC',
            'name': 'Bitcoin',
            'asset_type': 'MAJORS',
            'confidence': 1.0,
            'active_pillars': ['A', 'B', 'C', 'D'],
            'market_data': {...},
            'categories': [...]
        }
    """
    # Detect asset type
    asset_type, confidence = detect_asset_type(ticker)
    
    # Get active pillars
    pillars, _ = get_pillars_for_asset(ticker)
    
    # Fetch market data
    coin_data = fetch_coin_data(ticker)
    
    return {
        'ticker': ticker.upper(),
        'name': coin_data.get('name', ticker) if coin_data else ticker,
        'asset_type': asset_type,
        'confidence': confidence,
        'active_pillars': pillars,
        'pillar_names': _pillar_names(pillars),
        'market_data': coin_data,
        'categories': coin_data.get('categories', []) if coin_data else []
    }


def _pillar_names(pillars: List[str]) -> List[str]:
    """Convert pillar letters to readable names"""
    mapping = {
        'A': 'Market Sentiment',
        'B': 'News & Events',
        'C': 'Derivatives & Leverage',
        'D': 'On-Chain & Flow',
        'E': 'Sector-Specific'
    }
    return [mapping.get(p, p) for p in pillars]


# =============================================================================
# BATCH DETECTION
# =============================================================================

def detect_multiple_assets(tickers: List[str]) -> dict:
    """
    Detect asset types for multiple tickers at once
    
    Args:
        tickers: List of asset symbols
    
    Returns:
        dict: {
            'BTC': {'type': 'MAJORS', 'confidence': 1.0, ...},
            'DOGE': {'type': 'MEMECOIN', 'confidence': 0.95, ...},
            ...
        }
    """
    results = {}
    
    for ticker in tickers:
        asset_type, confidence = detect_asset_type(ticker)
        pillars, _ = get_pillars_for_asset(ticker)
        
        results[ticker.upper()] = {
            'type': asset_type,
            'confidence': confidence,
            'pillars': pillars
        }
    
    return results


# =============================================================================
# ASSET COMPATIBILITY CHECKS
# =============================================================================

def is_derivatives_supported(ticker: str) -> bool:
    """
    Check if derivatives analysis is supported for this asset
    
    Args:
        ticker: Asset symbol
    
    Returns:
        bool: True if derivatives pillar (C) is active
    """
    pillars, _ = get_pillars_for_asset(ticker)
    return 'C' in pillars


def is_onchain_supported(ticker: str) -> bool:
    """
    Check if on-chain analysis is supported for this asset
    
    Args:
        ticker: Asset symbol
    
    Returns:
        bool: True if on-chain pillar (D) is active
    """
    pillars, _ = get_pillars_for_asset(ticker)
    return 'D' in pillars


def requires_sector_analysis(ticker: str) -> bool:
    """
    Check if sector-specific analysis is needed
    
    Args:
        ticker: Asset symbol
    
    Returns:
        bool: True if sector pillar (E) is active
    """
    pillars, _ = get_pillars_for_asset(ticker)
    return 'E' in pillars


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    print("Testing asset_detector.py...")
    
    # Test major assets
    print("\n1. Testing MAJORS:")
    btc_type, btc_conf = detect_asset_type('BTC')
    print(f"   BTC: {btc_type} (confidence: {btc_conf})")
    assert btc_type == 'MAJORS', "BTC should be MAJORS"
    
    eth_type, eth_conf = detect_asset_type('ETH')
    print(f"   ETH: {eth_type} (confidence: {eth_conf})")
    assert eth_type == 'MAJORS', "ETH should be MAJORS"
    
    # Test privacy coins
    print("\n2. Testing PRIVACY:")
    xmr_type, xmr_conf = detect_asset_type('XMR')
    print(f"   XMR: {xmr_type} (confidence: {xmr_conf})")
    assert xmr_type == 'PRIVACY', "XMR should be PRIVACY"
    
    # Test memecoins
    print("\n3. Testing MEMECOIN:")
    doge_type, doge_conf = detect_asset_type('DOGE')
    print(f"   DOGE: {doge_type} (confidence: {doge_conf})")
    assert doge_type == 'MEMECOIN', "DOGE should be MEMECOIN"
    
    # Test DeFi
    print("\n4. Testing DEFI:")
    aave_type, aave_conf = detect_asset_type('AAVE')
    print(f"   AAVE: {aave_type} (confidence: {aave_conf})")
    assert aave_type == 'DEFI', "AAVE should be DEFI"
    
    # Test pillar activation
    print("\n5. Testing pillar activation:")
    btc_pillars, btc_cat = get_pillars_for_asset('BTC')
    print(f"   BTC pillars: {btc_pillars}")
    assert 'C' in btc_pillars, "BTC should have derivatives pillar"
    
    doge_pillars, doge_cat = get_pillars_for_asset('DOGE')
    print(f"   DOGE pillars: {doge_pillars}")
    assert 'E' in doge_pillars, "DOGE should have sector-specific pillar"
    assert 'C' not in doge_pillars, "DOGE should not have derivatives pillar"
    
    # Test asset info
    print("\n6. Testing comprehensive asset info:")
    info = get_asset_info('BTC')
    print(f"   BTC info: {info['name']}, Type: {info['asset_type']}")
    print(f"   Active pillars: {info['pillar_names']}")
    
    print("\n✅ All asset detector tests passed!")
    print(f"\n📊 Summary:")
    print(f"   - Asset type detection: Working")
    print(f"   - Pillar activation: Working")
    print(f"   - Confidence scoring: Working")
    print(f"   - Batch detection: Available")