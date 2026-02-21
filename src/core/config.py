"""
File 2: Configuration Management
Dependencies: None
Status: ✅ COMPLETE

Purpose:
- Load API keys from environment variables
- Define asset type classifications
- Set rate limiting parameters
- Configure pillar activation rules per asset type
"""

from os import getenv
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# API CONFIGURATIONS
# =============================================================================

# CoinGecko API (Market data, coin info)
COINGECKO_API_KEY = getenv('COINGECKO_API_KEY', '')
COINGECKO_BASE_URL = 'https://api.coingecko.com/api/v3'

# Binance API (Derivatives data - funding, OI, liquidations)
BINANCE_API_KEY = getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = getenv('BINANCE_API_SECRET', '')
BINANCE_BASE_URL = 'https://fapi.binance.com'  # Futures API

# CryptoPanic API (News aggregation)
CRYPTOPANIC_API_KEY = getenv('CRYPTOPANIC_API_KEY', '')
CRYPTOPANIC_BASE_URL = 'https://cryptopanic.com/api/developer/v2'

# Alternative.me (Fear & Greed Index - No key needed)
FEAR_GREED_URL = 'https://api.alternative.me/fng/'

# Glassnode API (On-chain data - Optional, paid)
GLASSNODE_API_KEY = getenv('GLASSNODE_API_KEY', '')
GLASSNODE_BASE_URL = 'https://api.glassnode.com/v1/metrics'

# =============================================================================
# ASSET TYPE CLASSIFICATIONS
# =============================================================================

ASSET_TYPES = {
    'MAJORS': [
        'BTC', 'BITCOIN',
        'ETH', 'ETHEREUM'
    ],
    
    'PRIVACY': [
        'XMR', 'MONERO',
        'ZEC', 'ZCASH',
        'DASH',
        'SCRT', 'SECRET',
        'ARRR', 'PIRATE-CHAIN',
        'BEAM',
        'GRIN'
    ],
    
    'DEFI': [
        'AAVE',
        'UNI', 'UNISWAP',
        'CRV', 'CURVE-DAO-TOKEN',
        'COMP', 'COMPOUND',
        'MKR', 'MAKER',
        'SNX', 'SYNTHETIX',
        'SUSHI', 'SUSHI',
        'YFI', 'YEARN-FINANCE',
        '1INCH',
        'BAL', 'BALANCER',
        'LDO', 'LIDO-DAO'
    ],
    
    'MEMECOIN': [
        'DOGE', 'DOGECOIN',
        'SHIB', 'SHIBA-INU',
        'PEPE',
        'FLOKI',
        'BONK',
        'WIF', 'DOGWIFHAT',
        'BRETT',
        'MEW',
        'POPCAT'
    ]
}

# Flatten for quick lookups
_MAJORS_SET = set([coin.upper() for coin in ASSET_TYPES['MAJORS']])
_PRIVACY_SET = set([coin.upper() for coin in ASSET_TYPES['PRIVACY']])
_DEFI_SET = set([coin.upper() for coin in ASSET_TYPES['DEFI']])
_MEMECOIN_SET = set([coin.upper() for coin in ASSET_TYPES['MEMECOIN']])

# =============================================================================
# PILLAR ACTIVATION RULES
# =============================================================================
# Which analysis pillars to activate for each asset type
# A = Sentiment, B = News, C = Derivatives, D = On-Chain, E = Sector-Specific

PILLAR_ACTIVATION_RULES = {
    'MAJORS': ['A', 'B', 'C', 'D'],       # All core pillars
    'MEMECOIN': ['A', 'B', 'D', 'E'],     # Skip derivatives, add sector logic
    'PRIVACY': ['A', 'B', 'D', 'E'],      # Skip derivatives, add sector logic
    'DEFI': ['A', 'B', 'D', 'E'],         # Skip derivatives, add sector logic
    'OTHER': ['A', 'B', 'C', 'D']         # Default to core pillars
}

# =============================================================================
# RATE LIMITING
# =============================================================================

# API rate limits (requests per minute)
MAX_REQUESTS_PER_MINUTE = int(getenv('MAX_REQUESTS_PER_MINUTE', 30))
REQUEST_DELAY_SECONDS = 60 / MAX_REQUESTS_PER_MINUTE  # ~2 seconds default

# Per-API rate limits
RATE_LIMITS = {
    'coingecko': {
        'free': 10,      # requests per minute for free tier
        'demo': 30,      # Demo API key
        'pro': 500       # Pro API key
    },
    'binance': {
        'weight_limit': 2400,  # Weight limit per minute
        'order_limit': 1200     # Order limit per 10 seconds
    },
    'cryptopanic': {
        'free': 50       # requests per day for free tier
    }
}

# =============================================================================
# CACHE SETTINGS
# =============================================================================

CACHE_ENABLED = getenv('CACHE_ENABLED', 'true').lower() == 'true'
CACHE_TTL_SECONDS = int(getenv('CACHE_TTL_SECONDS', 300))  # 5 minutes default

# Per-data-type TTL (in seconds)
CACHE_TTL = {
    'coin_data': 300,        # 5 minutes
    'market_chart': 180,     # 3 minutes
    'funding_rate': 60,      # 1 minute (changes frequently)
    'open_interest': 120,    # 2 minutes
    'news': 600,             # 10 minutes
    'fear_greed': 3600,      # 1 hour (updates daily)
    'onchain': 1800          # 30 minutes
}

# Cache directory
CACHE_DIR = Path(__file__).parent.parent.parent / 'data' / 'cache'

# =============================================================================
# ANALYSIS SETTINGS
# =============================================================================

# Time windows for analysis
TIMEFRAMES = {
    'snapshot': '24h',       # Main analysis window
    'short': '1h',          # For rapid changes
    'medium': '7d',         # For context
    'long': '30d'           # For trends
}

# Thresholds for risk levels
RISK_THRESHOLDS = {
    'leverage': {
        'low': 0.01,        # Funding rate < 1%
        'medium': 0.03,     # 1-3%
        'high': 0.05        # > 5%
    },
    'liquidations': {
        'low': 1_000_000,   # < $1M USD
        'medium': 10_000_000,  # $1-10M
        'high': 50_000_000     # > $50M
    },
    'volume_spike': {
        'low': 1.5,         # 50% increase
        'medium': 2.0,      # 100% increase
        'high': 3.0         # 200% increase
    }
}

# =============================================================================
# VALIDATION
# =============================================================================

def validate_config():
    """
    Ensure all required API keys are present
    
    Returns:
        tuple: (is_valid, missing_keys, warnings)
    """
    # Required keys (at minimum, need CoinGecko for basic functionality)
    required = {
        'COINGECKO_API_KEY': COINGECKO_API_KEY
    }
    
    # Optional but recommended
    optional = {
        'BINANCE_API_KEY': BINANCE_API_KEY,
        'CRYPTOPANIC_API_KEY': CRYPTOPANIC_API_KEY
    }
    
    missing_required = [k for k, v in required.items() if not v]
    missing_optional = [k for k, v in optional.items() if not v]
    
    is_valid = len(missing_required) == 0
    
    warnings = []
    if missing_optional:
        warnings.append(f"Optional keys missing: {', '.join(missing_optional)}")
        warnings.append("Some features will be limited.")
    
    return is_valid, missing_required, warnings


def get_asset_category(ticker: str) -> str:
    """
    Quick lookup for asset category
    
    Args:
        ticker: Asset symbol (e.g., 'BTC', 'DOGE')
    
    Returns:
        str: 'MAJORS', 'PRIVACY', 'DEFI', 'MEMECOIN', or 'OTHER'
    """
    ticker_upper = ticker.upper()
    
    if ticker_upper in _MAJORS_SET:
        return 'MAJORS'
    elif ticker_upper in _PRIVACY_SET:
        return 'PRIVACY'
    elif ticker_upper in _DEFI_SET:
        return 'DEFI'
    elif ticker_upper in _MEMECOIN_SET:
        return 'MEMECOIN'
    else:
        return 'OTHER'


def get_active_pillars(asset_category: str) -> list:
    """
    Get which pillars to activate for this asset category
    
    Args:
        asset_category: One of MAJORS, MEMECOIN, PRIVACY, DEFI, OTHER
    
    Returns:
        list: Pillar names ['A', 'B', 'C', ...]
    """
    return PILLAR_ACTIVATION_RULES.get(asset_category, PILLAR_ACTIVATION_RULES['OTHER'])


# =============================================================================
# AUTO-VALIDATION ON IMPORT
# =============================================================================

# Validate configuration when module is imported
_is_valid, _missing, _warnings = validate_config()

if not _is_valid:
    print(f"⚠️  Configuration Error: Missing required API keys: {', '.join(_missing)}")
    print("   Add these to your .env file to enable full functionality.")
elif _warnings:
    print("INFO: Configuration loaded with warnings:")
    for warning in _warnings:
        print(f"   {warning}")
else:
    print("SUCCESS: Configuration loaded successfully")

# =============================================================================
# TRAFFIC CONTROL RULES
# =============================================================================

POSTING_SCHEDULE = {
    # THREADS: The "Anchor" posts (Morning Scan, Mid-Day Update)
    'thread': {
        'gap_seconds': 21600,    # 6 Hours between threads
        'max_per_day': 4         # Limit to 4 big threads/day
    },
    
    # NEWS: The "Ticker" updates (Breaking news, single charts)
    'news_flash': {
        'gap_seconds': 300,      # ~5 minutes min gap (distributes the volume)
        'burst_limit': 3         # Allow 3 fast tweets if major news breaks
    },

    # GLOBAL SAFETY (The "Hard Limit")
    'global': {
        'semi_hourly_cap': 40,   # Never exceed 40 posts in 30 mins
        'daily_cap': 2300        # Never exceed 2300/day
    }
}