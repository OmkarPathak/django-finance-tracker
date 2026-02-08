import requests
from django.core.cache import cache
from decimal import Decimal

def get_exchange_rate(from_curr, to_curr):
    """
    Fetches the exchange rate between two currencies using Frankfurter API.
    Uses Django cache to avoid repeated external requests.
    """
    if from_curr == to_curr:
        return Decimal('1.0')

    # Currency mappings (if symbols are used in DB)
    symbol_to_code = {
        '₹': 'INR',
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY',
        'A$': 'AUD',
        'C$': 'CAD',
        'CHF': 'CHF',
        '元': 'CNY',
        '₩': 'KRW',
    }

    from_code = symbol_to_code.get(from_curr, from_curr)
    to_code = symbol_to_code.get(to_curr, to_curr)

    if from_code == to_code:
        return Decimal('1.0')

    cache_key = f"xr_{from_code}_{to_code}"
    cached_rate = cache.get(cache_key)
    if cached_rate:
        return Decimal(str(cached_rate))

    try:
        url = f"https://api.frankfurter.app/latest?from={from_code}&to={to_code}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data['rates'][to_code]
        
        # Cache for 24 hours
        cache.set(cache_key, rate, 60*60*24)
        return Decimal(str(rate))
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        # Return 1.0 as fallback to avoid breaking calculations
        return Decimal('1.0')
