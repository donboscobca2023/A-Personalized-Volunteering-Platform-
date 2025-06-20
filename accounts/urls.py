from django.urls import path
from .views import user_login, user_logout, register
from . import views

urlpatterns = [
    path("dashboard/volunteer/", views.volunteer_dashboard, name="volunteer_dashboard"),
    path("dashboard/ngo/", views.ngo_dashboard, name="ngo_dashboard"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("register/", register, name="register"),
    path("edit_account/", views.edit_account, name="edit_account"),
    path("profile/<int:user_id>/", views.user_profile, name="user_profile"),
    path("ngo_profile/<int:user_id>/", views.ngo_profile, name="ngo_profile"),
    path("report/<int:user_id>/", views.report_user, name="report_user"),
]
