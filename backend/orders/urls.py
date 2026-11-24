from django.urls import path

from . import views

urlpatterns = [
    path("checkout", views.CheckoutView.as_view()),
    path("orders", views.OrderListView.as_view()),
    path("orders/<int:order_id>", views.OrderDetailView.as_view()),
    path("orders/<int:order_id>/refresh", views.OrderRefreshView.as_view()),
    path("organizer/checkin", views.CheckInView.as_view()),
    path("webhooks/payment", views.PaymentWebhookView.as_view()),
]
