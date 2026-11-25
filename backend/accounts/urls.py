from django.urls import path

from . import views

urlpatterns = [
    path("csrf", views.CsrfView.as_view()),
    path("register", views.RegisterView.as_view()),
    path("login", views.LoginView.as_view()),
    path("login/2fa", views.LoginTwoFactorView.as_view()),
    path("2fa/setup", views.TwoFactorSetupView.as_view()),
    path("logout", views.LogoutView.as_view()),
    path("username-available", views.UsernameAvailableView.as_view()),
]
