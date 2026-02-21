"""
File 3: Helper Functions
Dependencies: config.py
Status: ✅ COMPLETE

Purpose:
- Common utility functions used across modules
- Timestamp handling, percentage calculators
- Risk level mappers (Low/Medium/High)
- Data validation functions
"""

from datetime import datetime, timezone
from typing import Union, Optional, Dict, Any
import re


# =============================================================================
# MATHEMATICAL HELPERS
# =============================================================================

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values
    
    Args:
        old_value: Original value
        new_value: New value
    
    Returns:
        float: Percentage change (e.g., 50.0 for 50% increase)
    
    Examples:
        >>> calculate_percentage_change(100, 150)
        50.0
        >>> calculate_percentage_change(100, 50)
        -50.0
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')
    
    return ((new_value - old_value) / abs(old_value)) * 100


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero
    
    Args:
        numerator: Top of division
        denominator: Bottom of division
        default: Value to return if denominator is 0
    
    Returns:
        float: Result of division or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_velocity(volume: float, market_cap: float) -> float:
    """
    Calculate volume velocity (volume/market_cap ratio)
    Higher velocity = more speculative trading
    
    Args:
        volume: 24h trading volume
        market_cap: Current market cap
    
    Returns:
        float: Velocity ratio
    """
    return safe_divide(volume, market_cap, 0.0)


# =============================================================================
# RISK LEVEL MAPPING
# =============================================================================

def map_to_risk_level(value: float, thresholds: Dict[str, float]) -> str:
    """
    Map a numeric value to a risk level category
    
    Args:
        value: Numeric value to categorize
        thresholds: Dict with 'low', 'medium', 'high' thresholds
    
    Returns:
        str: 'Low', 'Medium', or 'High'
    
    Example:
        >>> thresholds = {'low': 0.01, 'medium': 0.03, 'high': 0.05}
        >>> map_to_risk_level(0.02, thresholds)
        'Medium'
    """
    if value < thresholds.get('low', 0):
        return 'Low'
    elif value < thresholds.get('medium', 0):
        return 'Medium'
    elif value < thresholds.get('high', 0):
        return 'Medium'
    else:
        return 'High'


def categorize_funding_rate(funding_rate: float) -> Dict[str, Any]:
    """
    Categorize funding rate into risk level and signal
    
    Args:
        funding_rate: Current funding rate (e.g., 0.01 for 1%)
    
    Returns:
        dict: {
            'risk_level': 'Low'|'Medium'|'High',
            'signal': 'neutral'|'long_heavy'|'short_heavy',
            'description': str
        }
    """
    abs_rate = abs(funding_rate)
    
    # Determine risk level
    if abs_rate < 0.01:
        risk_level = 'Low'
    elif abs_rate < 0.03:
        risk_level = 'Medium'
    else:
        risk_level = 'High'
    
    # Determine positioning signal
    if funding_rate > 0.005:
        signal = 'long_heavy'
        description = 'Longs paying shorts - overcrowded long positions'
    elif funding_rate < -0.005:
        signal = 'short_heavy'
        description = 'Shorts paying longs - overcrowded short positions'
    else:
        signal = 'neutral'
        description = 'Balanced positioning'
    
    return {
        'risk_level': risk_level,
        'signal': signal,
        'description': description
    }


# =============================================================================
# TIMESTAMP HELPERS
# =============================================================================

def format_timestamp(unix_timestamp: Union[int, float], format_str: str = '%Y-%m-%d %H:%M:%S UTC') -> str:
    """
    Convert Unix timestamp to human-readable format
    
    Args:
        unix_timestamp: Unix timestamp (seconds since epoch)
        format_str: strftime format string
    
    Returns:
        str: Formatted timestamp
    
    Examples:
        >>> format_timestamp(1704067200)
        '2024-01-01 00:00:00 UTC'
    """
    try:
        dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        return dt.strftime(format_str)
    except (ValueError, OSError):
        return 'Invalid timestamp'


def get_current_timestamp() -> int:
    """
    Get current Unix timestamp
    
    Returns:
        int: Current timestamp in seconds
    """
    return int(datetime.now(timezone.utc).timestamp())


def time_ago(unix_timestamp: Union[int, float]) -> str:
    """
    Convert timestamp to relative time string (e.g., '2 hours ago')
    
    Args:
        unix_timestamp: Unix timestamp
    
    Returns:
        str: Human-readable relative time
    """
    now = datetime.now(timezone.utc)
    dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)} minutes ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)} hours ago"
    else:
        return f"{int(seconds / 86400)} days ago"


# =============================================================================
# VALIDATION
# =============================================================================

def validate_ticker(ticker: str) -> bool:
    """
    Validate that a ticker symbol is properly formatted
    
    Args:
        ticker: Ticker symbol to validate
    
    Returns:
        bool: True if valid, False otherwise
    
    Rules:
        - 1-10 characters
        - Alphanumeric and hyphens only
        - Not empty
    """
    if not ticker or not isinstance(ticker, str):
        return False
    
    # Length check
    if len(ticker) < 1 or len(ticker) > 20:
        return False
    
    # Character check (alphanumeric, hyphens, underscores)
    pattern = r'^[A-Za-z0-9\-_]+$'
    return bool(re.match(pattern, ticker))


def validate_percentage(value: float, min_val: float = -100, max_val: float = 1000) -> bool:
    """
    Validate that a percentage value is reasonable
    
    Args:
        value: Percentage value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    
    Returns:
        bool: True if valid
    """
    return isinstance(value, (int, float)) and min_val <= value <= max_val


# =============================================================================
# DATA FORMATTING
# =============================================================================

def format_large_number(number: float, decimals: int = 2) -> str:
    """
    Format large numbers with K, M, B suffixes
    
    Args:
        number: Number to format
        decimals: Number of decimal places
    
    Returns:
        str: Formatted number
    
    Examples:
        >>> format_large_number(1500)
        '1.50K'
        >>> format_large_number(2500000)
        '2.50M'
    """
    if abs(number) < 1000:
        return f"{number:.{decimals}f}"
    elif abs(number) < 1_000_000:
        return f"{number/1000:.{decimals}f}K"
    elif abs(number) < 1_000_000_000:
        return f"{number/1_000_000:.{decimals}f}M"
    else:
        return f"{number/1_000_000_000:.{decimals}f}B"


def format_currency(amount: float, currency: str = 'USD', decimals: int = 2) -> str:
    """
    Format a number as currency
    
    Args:
        amount: Amount to format
        currency: Currency symbol
        decimals: Decimal places
    
    Returns:
        str: Formatted currency string
    """
    if currency == 'USD':
        return f"${amount:,.{decimals}f}"
    else:
        return f"{amount:,.{decimals}f} {currency}"


def truncate_string(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate a string to max length
    
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        str: Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


# =============================================================================
# DATA STRUCTURE HELPERS
# =============================================================================

def safe_get(data: Dict, *keys, default=None):
    """
    Safely get nested dictionary values
    
    Args:
        data: Dictionary to search
        *keys: Keys to traverse
        default: Default value if not found
    
    Returns:
        Value at keys or default
    
    Example:
        >>> data = {'a': {'b': {'c': 123}}}
        >>> safe_get(data, 'a', 'b', 'c')
        123
        >>> safe_get(data, 'a', 'x', 'y', default=0)
        0
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def merge_dicts(*dicts) -> Dict:
    """
    Merge multiple dictionaries (later values override earlier)
    
    Args:
        *dicts: Dictionaries to merge
    
    Returns:
        dict: Merged dictionary
    """
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result


# =============================================================================
# TESTING HELPERS
# =============================================================================

if __name__ == '__main__':
    # Run basic tests
    print("Testing helpers.py...")
    
    # Test percentage change
    assert calculate_percentage_change(100, 150) == 50.0
    assert calculate_percentage_change(100, 50) == -50.0
    print("✓ calculate_percentage_change")
    
    # Test safe divide
    assert safe_divide(10, 2) == 5.0
    assert safe_divide(10, 0, default=-1) == -1
    print("✓ safe_divide")
    
    # Test risk mapping
    thresholds = {'low': 0.01, 'medium': 0.03, 'high': 0.05}
    assert map_to_risk_level(0.005, thresholds) == 'Low'
    assert map_to_risk_level(0.02, thresholds) == 'Medium'
    print("✓ map_to_risk_level")
    
    # Test ticker validation
    assert validate_ticker('BTC') == True
    assert validate_ticker('') == False
    assert validate_ticker('BTC-USD') == True
    print("✓ validate_ticker")
    
    # Test number formatting
    assert format_large_number(1500) == '1.50K'
    assert format_large_number(2_500_000) == '2.50M'
    print("✓ format_large_number")
    
    print("\n✅ All helper tests passed!")