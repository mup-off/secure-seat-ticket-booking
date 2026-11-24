from django.urls import path

from .dev_views import DevPayView

urlpatterns = [path("orders/<int:order_id>/pay", DevPayView.as_view())]
