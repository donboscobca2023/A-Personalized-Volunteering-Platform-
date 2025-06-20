from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, RegistrationForm, EditAccountForm, ReviewForm, ReportForm
from feeds.models import Application, Opportunity
from .models import Report
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Avg


def index(request):
    return render(request, "index.html")


def user_login(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirect based on role
            if user.role == "admin":
                return redirect("/accounts/admin_dashboard/")
            elif user.role == "ngo":
                return redirect("/accounts/dashboard/ngo/")

            else:
                return redirect("/accounts/dashboard/volunteer")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("home")


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if user.role == "admin":
                user.is_staff = True  # Just in case you want to allow admin creation (optional)
            user.skills = form.cleaned_data.get("skills", "")
            user.save()
            login(request, user)  # Auto-login after registration
            if user.role == "ngo":
                return redirect("/accounts/dashboard/ngo/")
            else:
                return redirect("/accounts/dashboard/volunteer/")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def volunteer_dashboard(request):
    if request.user.role != "volunteer":
        return redirect("home")
    # Get all applications for this volunteer
    applications = Application.objects.filter(volunteer=request.user).select_related("opportunity").order_by("-applied_at")
    return render(request, "accounts/volunteer_dashboard.html", {"applications": applications})


@login_required
def ngo_dashboard(request):
    if request.user.role != "ngo":
        return redirect("home")
    return render(request, "accounts/ngo_dashboard.html")


@login_required
def edit_account(request):
    if request.method == "POST":
        form = EditAccountForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("volunteer_dashboard" if request.user.role == "volunteer" else "ngo_dashboard")
    else:
        form = EditAccountForm(instance=request.user)
    return render(request, "accounts/edit_account.html", {"form": form})


@login_required
def user_profile(request, user_id):
    User = get_user_model()
    user_obj = get_object_or_404(User, id=user_id)
    applications = Application.objects.filter(volunteer=user_obj, status="completed").select_related("opportunity").order_by("-completed_at")
    reviews = applications.exclude(review="").exclude(review__isnull=True)
    avg_rating = reviews.aggregate(avg=Avg("review_rating"))['avg']
    return render(request, "accounts/profile.html", {"profile_user": user_obj, "applications": applications, "reviews": reviews, "avg_rating": avg_rating})


@login_required
def report_user(request, user_id):
    User = get_user_model()
    reported = get_object_or_404(User, id=user_id)
    # Only allow volunteers to report NGOs and NGOs to report volunteers
    if (request.user.role == "volunteer" and reported.role != "ngo") or (request.user.role == "ngo" and reported.role != "volunteer"):
        return render(request, "403.html")
    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported = reported
            report.report_type = reported.role
            report.save()
            return redirect("user_profile", user_id=reported.id)
    else:
        form = ReportForm()
    return render(request, "accounts/report_user.html", {"form": form, "reported": reported})


@login_required
def ngo_profile(request, user_id):
    User = get_user_model()
    ngo = get_object_or_404(User, id=user_id, role="ngo")
    opportunities = Opportunity.objects.filter(ngo=ngo).order_by("-created_at")
    # Optionally, show reviews of this NGO (if you want to add reviews for NGOs in the future)
    return render(request, "accounts/ngo_profile.html", {"ngo": ngo, "opportunities": opportunities})
