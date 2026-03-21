from django.conf import settings


def google_analytics(request):
    """
    Adds GOOGLE_ANALYTICS_ID to the context if it exists in settings.
    """
    return {
        'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', None)
    }
