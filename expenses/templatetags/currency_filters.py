from django import template

register = template.Library()

@register.filter
def humanize_currency(value, currency_symbol='₹'):
    """
    Formats a number to a human-readable format based on currency.
    ₹ (Rupee): 
        >= 1Cr -> 1.25Cr
        >= 1L  -> 3.5L
        >= 1k  -> 35k
    Others: 
        >= 1B  -> 1.5B
        >= 1M  -> 1.5M
        >= 1k  -> 1.5k
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value

    if value < 1000 and value > -1000:
        return f"{value:.0f}"

    abs_value = abs(value)
    
    def format_num(num, divisor, suffix):
        result = num / divisor
        # Check if it's a whole number (e.g. 35.0) -> display as 35 (no decimals)
        # Otherwise display with 1 or 2 decimals
        if result % 1 == 0:
            return f"{result:.0f}{suffix}"
        return f"{result:.1f}{suffix}"

    if currency_symbol == '₹':
        if abs_value >= 10000000: # 1 Crore
            return format_num(value, 10000000, 'Cr')
        elif abs_value >= 100000: # 1 Lakh
            return format_num(value, 100000, 'L')
        elif abs_value >= 1000:   # 1 Thousand
            return format_num(value, 1000, 'k')
    else:
        if abs_value >= 1000000000: # 1 Billion
            return format_num(value, 1000000000, 'B')
        elif abs_value >= 1000000: # 1 Million
            return format_num(value, 1000000, 'M')
        elif abs_value >= 1000:    # 1 Thousand
            return format_num(value, 1000, 'k')
    
    return f"{value:.0f}"
