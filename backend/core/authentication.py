from rest_framework.authentication import SessionAuthentication


class StrictSessionAuthentication(SessionAuthentication):
    """Session authentication that checks the CSRF token on EVERY unsafe request.

    Django REST framework's own SessionAuthentication checks CSRF only for users who
    are already signed in. That would leave login and sign-up open to login-CSRF
    (an attacker's page signing the victim into the attacker's account). This class
    checks the token first, signed in or not. Safe methods (GET, HEAD, OPTIONS) are
    not checked, as in Django.
    """

    def authenticate(self, request):
        self.enforce_csrf(request)
        return super().authenticate(request)
