from django.conf import settings
from django.urls import include, path, re_path

from core.views import spa_index

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    path("api/", include("events.urls")),
    path("api/", include("orders.urls")),
]

if not settings.IS_PRODUCTION:
    # Development only: buttons that play the part of the buyer's phone.
    urlpatterns.append(path("api/dev/", include("orders.dev_urls")))

# Everything else is the React app (production build). Must stay last.
urlpatterns.append(re_path(r"^(?!api/|static/).*$", spa_index))
