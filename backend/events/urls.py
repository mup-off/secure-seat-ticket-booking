from django.urls import path

from . import views

urlpatterns = [
    path("events", views.EventListView.as_view()),
    path("events/<int:event_id>", views.EventDetailView.as_view()),
    path("organizer/events", views.OrganizerEventsView.as_view()),
    path("organizer/events/<int:event_id>", views.OrganizerEventDetailView.as_view()),
    path("organizer/events/<int:event_id>/ticket-types", views.TicketTypeCreateView.as_view()),
    path("organizer/events/<int:event_id>/cancel", views.EventCancelView.as_view()),
    path("organizer/events/<int:event_id>/attendees", views.AttendeeListView.as_view()),
]
