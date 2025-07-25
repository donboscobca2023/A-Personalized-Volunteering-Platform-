from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, RegistrationForm, EditAccountForm, ReviewForm, ReportForm
from feeds.models import Application, Opportunity
from .models import Report
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Avg
from django.views.decorators.http import require_http_methods


def index(request):
    return render(request, "index.html")


def user_login(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirect based on role
            if getattr(user, 'role', None) == "admin" or user.is_superuser:
                return redirect("/accounts/admin_dashboard/")
            elif getattr(user, 'role', None) == "ngo":
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
    User = get_user_model()
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if user.role == "admin":
                # If this is the first admin, approve immediately
                if not User.objects.filter(role="admin").exists():
                    user.is_staff = True
                    user.is_active = True
                else:
                    user.is_staff = False  # Not active admin yet
                    user.is_active = False  # Require approval
            user.skills = form.cleaned_data.get("skills", "")
            user.save()
            if user.role == "ngo":
                login(request, user)
                return redirect("/accounts/dashboard/ngo/")
            elif user.role == "volunteer":
                login(request, user)
                return redirect("/accounts/dashboard/volunteer/")
            elif user.role == "admin" and user.is_active:
                login(request, user)
                return redirect("/accounts/admin_dashboard/")
            else:
                # Show a message: Awaiting admin approval
                return render(request, "accounts/register.html", {"form": RegistrationForm(), "pending_admin": True})
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
    # Admin delete logic
    if request.method == "POST" and request.user.role == "admin" and user_obj.role in ["volunteer", "ngo"]:
        if request.POST.get("delete_user_id") == str(user_obj.id):
            user_obj.delete()
            return redirect("admin_dashboard")
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
    if request.method == "POST" and request.user.role == "admin":
        if request.POST.get("delete_user_id") == str(ngo.id):
            ngo.delete()
            return redirect("admin_dashboard")
    opportunities = Opportunity.objects.filter(ngo=ngo).order_by("-created_at")
    # Optionally, show reviews of this NGO (if you want to add reviews for NGOs in the future)
    return render(request, "accounts/ngo_profile.html", {"ngo": ngo, "opportunities": opportunities})


@login_required
@require_http_methods(["GET", "POST"])
def admin_dashboard(request):
    if not hasattr(request.user, 'role') or request.user.role != "admin":
        return render(request, "403.html")
    User = get_user_model()
    if request.method == "POST":
        if "report_id" in request.POST:
            report_id = request.POST.get("report_id")
            resolution = request.POST.get("resolution")
            if report_id and resolution:
                try:
                    report = Report.objects.get(id=report_id, handled=False)
                    report.handled = True
                    report.handled_by = request.user
                    report.handled_at = timezone.now()
                    report.resolution = resolution
                    report.save()
                except Report.DoesNotExist:
                    pass
        elif "approve_admin_id" in request.POST:
            admin_id = request.POST.get("approve_admin_id")
            try:
                admin_user = User.objects.get(id=admin_id, role="admin", is_active=False)
                admin_user.is_active = True
                admin_user.is_staff = True
                admin_user.save()
            except User.DoesNotExist:
                pass
        elif "delete_user_id" in request.POST:
            user_id = request.POST.get("delete_user_id")
            try:
                user_to_delete = User.objects.get(id=user_id)
                if user_to_delete.role in ["volunteer", "ngo"]:
                    user_to_delete.delete()
            except User.DoesNotExist:
                pass
    reports = Report.objects.all().order_by("-created_at")
    pending_admins = User.objects.filter(role="admin", is_active=False)
    users_to_manage = User.objects.filter(role__in=["volunteer", "ngo"]).order_by("role", "username")
    return render(request, "accounts/admin_dashboard.html", {"reports": reports, "pending_admins": pending_admins, "users_to_manage": users_to_manage})
