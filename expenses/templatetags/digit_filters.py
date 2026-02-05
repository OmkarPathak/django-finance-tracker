from django import template
from django.utils.translation import get_language

register = template.Library()

@register.filter
def translate_digits(value):
    if value is None:
        return ""
    
    lang = get_language()
    if lang not in ['mr', 'hi']:
        return value
    
    value_str = str(value)
    arabic_to_devanagari = {
        '0': '०', '1': '१', '2': '२', '3': '३', '4': '४',
        '5': '५', '6': '६', '7': '७', '8': '८', '9': '९'
    }
    
    return ''.join(arabic_to_devanagari.get(char, char) for char in value_str)
