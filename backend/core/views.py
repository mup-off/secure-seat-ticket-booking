from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe


@require_safe
@ensure_csrf_cookie
def spa_index(request):
    """Serves the built React app (frontend/dist/index.html) for any non-API path."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        return HttpResponseNotFound("Frontend not built. In development run the Vite dev server (npm run dev).")
    return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
