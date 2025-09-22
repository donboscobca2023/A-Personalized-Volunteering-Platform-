from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Opportunity, Application, Task
from .forms import OpportunityForm, TaskForm
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from accounts.forms import ReviewForm
from django.http import HttpResponseForbidden


def general_feed(request):
    opportunities = Opportunity.objects.filter(end_date__gte=timezone.now().date()).order_by("-created_at")
    user_applications = set()
    recommended = []
    new = list(opportunities)
    show = request.GET.get("show", "new")
    if request.user.is_authenticated and request.user.role == "volunteer":
        user_skills = [s.strip().lower() for s in (request.user.skills or "").split(",") if s.strip()]
        if user_skills:
            def skill_match(opp):
                opp_skills = [s.strip().lower() for s in (opp.skills_recommended or "").split(",") if s.strip()]
                return len(set(user_skills) & set(opp_skills)) > 0
            recommended = [opp for opp in opportunities if skill_match(opp)]
            new = list(opportunities)  # allow overlap
        user_applications = set(
            Application.objects.filter(volunteer=request.user).values_list("opportunity_id", flat=True)
        )
    context = {
        "recommended": recommended,
        "new": new,
        "user_applications": user_applications,
        "show": show,
    }
    return render(request, "feeds/general_feed.html", context)


@login_required
def ngo_opportunities(request):
    if request.user.role != "ngo":
        return render(request, "403.html")  # optional permission error page

    opportunities = Opportunity.objects.filter(ngo=request.user, end_date__gte=timezone.now().date()).order_by("-created_at")
    return render(request, "feeds/ngo_feed.html", {"opportunities": opportunities})


@login_required
def create_opportunity(request):
    if request.user.role != "ngo":
        return render(request, "403.html")  # Optional: restrict access

    if request.method == "POST":
        form = OpportunityForm(request.POST)
        if form.is_valid():
            opportunity = form.save(commit=False)
            opportunity.ngo = request.user
            opportunity.save()
            return redirect("ngo_opportunities")  # Redirect to their list
    else:
        form = OpportunityForm()
    return render(request, "feeds/create.html", {"form": form})


@login_required
def apply_for_opportunity(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id)

    # Only volunteers can apply
    if request.user.role != "volunteer":
        return redirect("general_feed")

    # Check if already applied
    if Application.objects.filter(
        opportunity=opportunity, volunteer=request.user
    ).exists():
        return redirect("general_feed")  # Or show a message

    Application.objects.create(opportunity=opportunity, volunteer=request.user)
    return redirect("volunteer_dashboard")


@login_required
def manage_applications(request, opportunity_id):
    if request.user.role != "ngo":
        return render(request, "403.html")
    opportunity = get_object_or_404(Opportunity, id=opportunity_id, ngo=request.user)
    #applications = Application.objects.filter(opportunity=opportunity)
    applications = Application.objects.filter(opportunity=opportunity).all().order_by("-applied_at")
    if request.method == "POST":
        app_id = request.POST.get("app_id")
        action = request.POST.get("action")
        application = get_object_or_404(Application, id=app_id, opportunity=opportunity)
        if action == "approve":
            application.status = "approved"
        elif action == "reject":
            application.status = "rejected"
        application.save()
        return redirect("manage_applications", opportunity_id=opportunity.id)
    return render(
        request,
        "feeds/manage_applications.html",
        {"opportunity": opportunity, "applications": applications},
    )


@login_required
def volunteer_feed(request):
    # Only for volunteers
    if request.user.role != "volunteer":
        return redirect("general_feed")
    user_skills = [s.strip().lower() for s in (request.user.skills or "").split(",") if s.strip()]
    all_opps = Opportunity.objects.filter(end_date__gte=timezone.now().date()).order_by("-created_at")
    if user_skills:
        def skill_match(opp):
            opp_skills = [s.strip().lower() for s in (opp.skills_recommended or "").split(",") if s.strip()]
            return len(set(user_skills) & set(opp_skills)) > 0
        recommended = [opp for opp in all_opps if skill_match(opp)]
        new = [opp for opp in all_opps if not skill_match(opp)]
    else:
        recommended = []
        new = list(all_opps)
    user_applications = set(
        Application.objects.filter(volunteer=request.user).values_list("opportunity_id", flat=True)
    )
    context = {
        "recommended": recommended,
        "new": new,
        "user_applications": user_applications,
    }
    return render(request, "feeds/volunteer_feed.html", context)


@login_required
def mark_application_completed(request, app_id):
    app = get_object_or_404(Application, id=app_id)
    if request.user != app.opportunity.ngo:
        return render(request, "403.html")
    if request.method == "POST":
        app.status = "completed"
        app.completed_at = timezone.now()
        app.save()
        return redirect("manage_applications", opportunity_id=app.opportunity.id)
    return render(request, "feeds/mark_completed.html", {"app": app})


@login_required
def review_application(request, app_id):
    app = get_object_or_404(Application, id=app_id)
    if request.user != app.opportunity.ngo or app.status != "completed":
        return render(request, "403.html")
    if request.method == "POST":
        form = ReviewForm(request.POST, instance=app)
        if form.is_valid():
            form.save()
            return redirect("manage_applications", opportunity_id=app.opportunity.id)
    else:
        form = ReviewForm(instance=app)
    return render(request, "feeds/review_application.html", {"form": form, "app": app})


@login_required
def edit_opportunity(request, opportunity_id):
    opportunity = get_object_or_404(Opportunity, id=opportunity_id, ngo=request.user)
    if request.user.role != "ngo":
        return render(request, "403.html")
    if request.method == "POST":
        form = OpportunityForm(request.POST, instance=opportunity)
        if form.is_valid():
            form.save()
            return redirect("ngo_opportunities")
    else:
        form = OpportunityForm(instance=opportunity)
    return render(request, "feeds/edit_opportunity.html", {"form": form, "opportunity": opportunity})


@login_required
def assign_task(request, app_id):
    app = get_object_or_404(Application, id=app_id)
    if request.user.role != "ngo" or app.opportunity.ngo != request.user or app.status != "approved":
        return HttpResponseForbidden()
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.application = app
            task.save()
            return redirect("manage_applications", opportunity_id=app.opportunity.id)
    else:
        form = TaskForm()
    return render(request, "feeds/assign_task.html", {"form": form, "app": app})


@login_required
def view_tasks(request, app_id):
    app = get_object_or_404(Application, id=app_id)
    if request.user != app.volunteer:
        return HttpResponseForbidden()
    tasks = app.tasks.all()
    return render(request, "feeds/view_tasks.html", {"tasks": tasks, "app": app})


@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.user != task.application.volunteer:
        return HttpResponseForbidden()
    if request.method == "POST":
        task.is_completed = True
        task.completed_at = timezone.now()
        task.save()
        return redirect("view_tasks", app_id=task.application.id)
    return render(request, "feeds/complete_task.html", {"task": task})
