from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from .forms import LoginForm, RegistrationForm, EditAccountForm, ReviewForm, ReportForm
from feeds.models import Application, Opportunity
from .models import Report
from django.utils import timezone
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from django.db.models import Avg
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta


def index(request):
    return render(request, "home.html")

def user_login(request):
    message = None
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if getattr(user, 'role', None) == "ngo" and not getattr(user, 'is_approved', True):
                message = "Your account is pending approval by an admin. You will be notified once approved."
                return render(request, "accounts/pending_approval.html", {"message": message})
            if getattr(user, 'role', None) == "admin" and not getattr(user, 'is_active', True):
                message = "Your admin account is pending approval. You will be notified once approved."
                return render(request, "accounts/pending_approval.html", {"message": message})
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
    message = None
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
            if user.role == "ngo":
                user.is_approved = False  # Require admin approval for NGOs
            user.skills = form.cleaned_data.get("skills", "")
            user.save()
            if user.role == "ngo" and not user.is_approved:
                message = "Your NGO account is pending approval by an admin. You will be notified once approved."
                return render(request, "accounts/pending_approval.html", {"message": message})
            elif user.role == "ngo":
                login(request, user)
                return redirect("/accounts/dashboard/ngo/")
            elif user.role == "volunteer":
                login(request, user)
                return redirect("/accounts/dashboard/volunteer/")
            elif user.role == "admin" and user.is_active:
                login(request, user)
                return redirect("/accounts/admin_dashboard/")
            elif user.role == "admin" and not user.is_active:
                message = "Your admin account is pending approval. You will be notified once approved."
                return render(request, "accounts/pending_approval.html", {"message": message})
            else:
                # Should not happen, fallback
                return redirect("home")
        else:
            # Form is invalid, show form with errors
            return render(request, "accounts/register.html", {"form": form})
    else:
        form = RegistrationForm()
        return render(request, "accounts/register.html", {"form": form})
# Pending approval dashboard for NGOs/admins
from django.contrib.auth.decorators import login_required

@login_required
def pending_approval_dashboard(request):
    # Only show for unapproved NGO or admin
    if getattr(request.user, 'role', None) == "ngo":
        if not getattr(request.user, 'is_approved', True):
            return render(request, "accounts/pending_approval.html")
        else:
            return redirect("/accounts/dashboard/ngo/")
    elif getattr(request.user, 'role', None) == "admin":
        if not getattr(request.user, 'is_active', True):
            return render(request, "accounts/pending_approval.html")
        else:
            return redirect("/accounts/admin_dashboard/")
    else:
        return redirect("home")


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
    # Get all opportunities posted by this NGO
    opportunities = Opportunity.objects.filter(ngo=request.user).order_by("-created_at")
    return render(request, "accounts/ngo_dashboard.html", {"opportunities": opportunities})


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
    # Only show certificate download if user is viewing their own profile
    show_certificate = request.user.is_authenticated and request.user.id == user_obj.id
    return render(request, "accounts/profile.html", {"profile_user": user_obj, "applications": applications, "reviews": reviews, "avg_rating": avg_rating, "show_certificate": show_certificate})


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
        elif "reject_admin_id" in request.POST:
            admin_id = request.POST.get("reject_admin_id")
            try:
                admin_user = User.objects.get(id=admin_id, role="admin", is_active=False)
                admin_user.delete()
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
        elif "approve_ngo_id" in request.POST:
            ngo_id = request.POST.get("approve_ngo_id")
            try:
                ngo_user = User.objects.get(id=ngo_id, role="ngo", is_approved=False)
                ngo_user.is_approved = True
                ngo_user.save()
            except User.DoesNotExist:
                pass
        elif "reject_ngo_id" in request.POST:
            ngo_id = request.POST.get("reject_ngo_id")
            try:
                ngo_user = User.objects.get(id=ngo_id, role="ngo", is_approved=False)
                ngo_user.delete()
            except User.DoesNotExist:
                pass
    pending_ngos = User.objects.filter(role="ngo", is_approved=False)
    pending_admins = User.objects.filter(role="admin", is_active=False)
    reports = Report.objects.all().order_by("-created_at")
    return render(request, "accounts/admin_dashboard.html", {
        "pending_admins": pending_admins,
        "pending_ngos": pending_ngos,
        "reports": reports,
    })


@login_required
def notifications(request):
    applications = []
    reports = []
    if request.user.role == "ngo":
        # Show applications for this NGO's opportunities that are not completed
        applications = Application.objects.filter(opportunity__ngo=request.user).exclude(status="completed").select_related("volunteer", "opportunity")
    if request.user.role == "admin":
        # Show all unhandled reports
        reports = Report.objects.filter(handled=False).select_related("reporter", "reported")
    return render(request, "accounts/notifications.html", {"applications": applications, "reports": reports})


@login_required
def download_certificate(request, app_id):
    app = get_object_or_404(Application, id=app_id, volunteer=request.user, status="completed")
    volunteer_name = request.user.username
    center_name = app.opportunity.ngo.username if hasattr(app.opportunity.ngo, 'username') else str(app.opportunity.ngo)
    event_name = app.opportunity.title
    event_date = app.completed_at if app.completed_at else app.opportunity.end_date

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{volunteer_name}_{event_name}.pdf"'

    p = canvas.Canvas(response, pagesize=landscape(letter))
    width, height = landscape(letter)

    bg_path = "static/img/volunteers-601662_1920.jpg"
    try:
        bg = ImageReader(bg_path)
        p.drawImage(bg, 0, 0, width, height, mask='auto')
    except Exception:
        p.setFillColor(HexColor("#f4f6fb"))
        p.rect(0, 0, width, height, fill=1, stroke=0)
        p.setFillColor(HexColor("#22c55e"))
        p.rect(0, height-1.5*inch, width, 1.5*inch, fill=1, stroke=0)

    # Border
    p.setStrokeColor(HexColor("#14532d"))
    p.setLineWidth(6)
    p.rect(0.5*inch, 0.5*inch, width-1*inch, height-1*inch, fill=0)

    # Title
    p.setFont("Helvetica-Bold", 38)
    p.setFillColor(HexColor("#14532d"))
    p.drawCentredString(width / 2, height - 1.1*inch, "Certificate of Participation")

    # Decorative line
    p.setStrokeColor(HexColor("#22c55e"))
    p.setLineWidth(3)
    p.line(width/2 - 3*inch, height - 1.35*inch, width/2 + 3*inch, height - 1.35*inch)

    # Subtitle
    p.setFont("Helvetica", 22)
    p.setFillColor(HexColor("#222222"))
    p.drawCentredString(width / 2, height - 2.1*inch, f"This certifies that")

    # Volunteer Name
    p.setFont("Helvetica-Bold", 30)
    p.setFillColor(HexColor("#0d3a1a"))
    p.drawCentredString(width / 2, height - 2.8*inch, volunteer_name)

    # Event and Center
    p.setFont("Helvetica", 22)
    p.setFillColor(HexColor("#222222"))
    p.drawCentredString(width / 2, height - 3.6*inch, f"volunteered for {event_name}")
    p.drawCentredString(width / 2, height - 4.2*inch, f"by {center_name}")
    p.drawCentredString(width / 2, height - 4.8*inch, f"on {event_date.strftime('%B %d, %Y') if hasattr(event_date, 'strftime') else event_date}")

    p.showPage()
    p.save()
    return response


def get_notification_count(request):
    if not request.user.is_authenticated:
        return {'notification_count': 0}
    count = 0
    if hasattr(request.user, 'role'):
        if request.user.role == 'ngo':
            from feeds.models import Application
            count = Application.objects.filter(opportunity__ngo=request.user, status='pending').count()
        elif request.user.role == 'admin':
            from .models import Report
            count = Report.objects.filter(handled=False).count()
    return {'notification_count': count}


@staff_member_required
def admin_statistics(request):
    now = timezone.now()
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_week = now - timedelta(days=now.weekday())
    start_week = start_week.replace(hour=0, minute=0, second=0, microsecond=0)
    start_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    User = get_user_model()
    stats = {
        'accounts_month': User.objects.filter(date_joined__gte=start_month).count(),
        'accounts_week': User.objects.filter(date_joined__gte=start_week).count(),
        'accounts_year': User.objects.filter(date_joined__gte=start_year).count(),
        'accounts_total': User.objects.count(),
        'reports_month': Report.objects.filter(created_at__gte=start_month).count(),
        'reports_week': Report.objects.filter(created_at__gte=start_week).count(),
        'reports_year': Report.objects.filter(created_at__gte=start_year).count(),
        'reports_total': Report.objects.count(),
        'opportunities_month': Opportunity.objects.filter(created_at__gte=start_month).count(),
        'opportunities_week': Opportunity.objects.filter(created_at__gte=start_week).count(),
        'opportunities_year': Opportunity.objects.filter(created_at__gte=start_year).count(),
        'opportunities_total': Opportunity.objects.count(),
    }
    return render(request, 'accounts/statistics.html', {'stats': stats})
