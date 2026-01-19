from django import template
from django.template.defaultfilters import stringfilter
import markdown as md
from django.utils.safestring import mark_safe
import bleach

register = template.Library()

@register.filter()
@stringfilter
def markdown(value):
    html_content = md.markdown(value, extensions=['markdown.extensions.fenced_code'])
    
    # Define allowed tags and attributes
    allowed_tags = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
        'p', 'b', 'i', 'strong', 'em', 'code', 'pre', 
        'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'br', 'hr',
        'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]
    
    allowed_attributes = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title'],
        '*': ['class'] # Allow classes for styling
    }
    
    cleaned_content = bleach.clean(
        html_content, 
        tags=allowed_tags, 
        attributes=allowed_attributes,
        strip=True
    )
    
    return mark_safe(cleaned_content)
