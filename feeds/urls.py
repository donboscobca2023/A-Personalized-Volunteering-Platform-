from django.urls import path
from . import views

urlpatterns = [
    path("", views.general_feed, name="general_feed"),
    path("volunteer/", views.volunteer_feed, name="volunteer_feed"),
    path("ngo/", views.ngo_opportunities, name="ngo_opportunities"),
    path("create/", views.create_opportunity, name="create_opportunity"),
    path(
        "edit/<int:opportunity_id>/",
        views.edit_opportunity,
        name="edit_opportunity",
    ),
    path(
        "apply/<int:opportunity_id>/",
        views.apply_for_opportunity,
        name="apply_for_opportunity",
    ),
    path(
        "manage_applications/<int:opportunity_id>/",
        views.manage_applications,
        name="manage_applications",
    ),
    path(
        "mark_completed/<int:app_id>/",
        views.mark_application_completed,
        name="mark_application_completed",
    ),
    path(
        "review_application/<int:app_id>/",
        views.review_application,
        name="review_application",
    ),
]
