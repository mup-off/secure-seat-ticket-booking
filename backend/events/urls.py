from django.urls import path

from . import views

E = "organizer/events/<int:event_id>"

urlpatterns = [
    path("events", views.EventListView.as_view()),
    path("events/<int:event_id>", views.EventDetailView.as_view()),
    path("events/<int:event_id>/unlock", views.EventUnlockView.as_view()),
    path("events/<int:event_id>/cover", views.EventCoverView.as_view()),
    path("organizer/events", views.OrganizerEventsView.as_view()),
    path(E, views.OrganizerEventDetailView.as_view()),
    path(f"{E}/cover", views.EventCoverUploadView.as_view()),
    path(f"{E}/ticket-types", views.TierListView.as_view()),
    path(f"{E}/ticket-types/reorder", views.TierReorderView.as_view()),
    path(f"{E}/ticket-types/<int:tier_id>", views.TierDetailView.as_view()),
    path(f"{E}/publish", views.EventStatusView.as_view(transition="publish")),
    path(f"{E}/pause", views.EventStatusView.as_view(transition="pause")),
    path(f"{E}/resume", views.EventStatusView.as_view(transition="resume")),
    path(f"{E}/cancel", views.EventStatusView.as_view(transition="cancel")),
    path(f"{E}/preview", views.EventPreviewView.as_view()),
    path(f"{E}/attendees", views.AttendeeListView.as_view()),
]
