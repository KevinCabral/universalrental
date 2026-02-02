from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class SessionTimeoutMiddleware:
    """
    Middleware to handle session timeout with user-friendly messages.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check session timeout for authenticated users
        if hasattr(request, 'user') and request.user.is_authenticated:
            session_age = getattr(settings, 'SESSION_COOKIE_AGE', 1800)  # Default 30 minutes
            last_activity = request.session.get('last_activity')
            
            if last_activity:
                try:
                    # Convert string back to datetime if needed
                    if isinstance(last_activity, str):
                        from django.utils.dateparse import parse_datetime
                        last_activity = parse_datetime(last_activity)
                    
                    # Check if session has expired
                    if last_activity and (timezone.now() - last_activity).total_seconds() > session_age:
                        # Session expired
                        request.session.flush()
                        messages.warning(request, 'A sua sessão expirou por motivos de segurança. Por favor, faça login novamente.')
                        return redirect(reverse('login'))
                except Exception:
                    # If there's any error parsing the datetime, just update it
                    pass
            
            # Update last activity for authenticated users
            request.session['last_activity'] = timezone.now().isoformat()

        response = self.get_response(request)
        return response
