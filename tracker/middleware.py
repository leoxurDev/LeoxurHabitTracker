import zoneinfo
from django.utils import timezone

class UserTimezoneMiddleware:
    """
    Middleware that activates the user's selected timezone for the request.
    Ensures timezone.localtime(), timezone.localdate(), and templates render
    in the user's exact timezone throughout the application.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = None
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            tzname = request.user.profile.timezone

        if not tzname:
            tzname = request.session.get('django_timezone')

        if tzname:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            except Exception:
                timezone.deactivate()
        else:
            timezone.deactivate()

        return self.get_response(request)
