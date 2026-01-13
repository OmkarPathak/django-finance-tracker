from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from django.urls import reverse

class DemoReadOnlyMiddleware:
    """
    Prevents the 'demo' user from making any state-changing requests (POST, PUT, DELETE).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.username == 'demo':
            # Allow logout POST request to pass through
            if request.path == reverse('account_logout'):
                return self.get_response(request)

            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                messages.warning(request, "⚠️ Demo Account: This action is restricted to read-only mode.")
                return redirect(request.META.get('HTTP_REFERER', '/'))

        response = self.get_response(request)
        return response

class TimezoneMiddleware:
    """
    Activates the timezone stored in the 'django_timezone' cookie.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import zoneinfo
        from django.utils import timezone
        
        tzname = request.COOKIES.get('django_timezone')
        if tzname:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            except Exception:
                # If cookie is invalid, fallback to default
                pass
        else:
            timezone.deactivate()
            
        return self.get_response(request)
