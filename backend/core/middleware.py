from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Adds the Content-Security-Policy header to every response (plan, Phase 3: XSS).

    Scripts, styles and images may only come from this site, and no other site may
    put SecureSeat in a frame. The React build contains no inline scripts, so the
    strict policy works without 'unsafe-inline'.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", settings.CONTENT_SECURITY_POLICY)
        return response
