import json

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import UserNamesForm, ProfileForm
from .models import Profile
from . import engine

FEATURES = [
    {"title": "Plain-English input",
     "text": "Describe the part the way you'd explain it to a colleague. No menus, no sketch tools, no CAD vocabulary required.",
     "cta": "Try a prompt"},
    {"title": "Clarifying questions",
     "text": "If a dimension or intent is missing, Friday asks a short question instead of guessing, so the model matches what you meant.",
     "cta": "See it in action"},
    {"title": "Validated before it's built",
     "text": "Every generated plan is checked against a schema and for geometry problems before any model is built.",
     "cta": "Try it out"},
    {"title": "Sketch-based modeling",
     "text": "Profiles are built as constrained sketches, so geometry stays tied to the dimensions you gave.",
     "cta": "Generate a part"},
    {"title": "Features and patterns",
     "text": "Parts are built up operation by operation: base shapes, cuts, features and repeating patterns.",
     "cta": "Try a pattern"},
    {"title": "Booleans and transforms",
     "text": "Combine, subtract and intersect bodies, then move, rotate or scale them into place.",
     "cta": "Try a prompt"},
    {"title": "Export",
     "text": "Download the finished model as a file you can take into your slicer, simulation or CAD tool.",
     "cta": "Build and download"},
]

EXAMPLES = [
    {"name": "Mounting plate", "tags": "Sketch · Extrude · Holes",
     "summary": "A flat plate with a pattern of corner holes: the classic first test for any text-to-CAD tool.",
     "prompt": "An 80 x 50 x 6 mm rectangular mounting plate with four 5 mm holes, 8 mm in from each corner.",
     "ops": ["Sketch", "Extrude", "Hole pattern"]},
    {"name": "Flanged bushing", "tags": "Revolved shape · Union · Bore",
     "summary": "A round part with a flange and a through bore, built from simple stacked cylinders.",
     "prompt": "A flanged bushing: 20 mm outer diameter, 12 mm bore, 25 mm long, with a 30 mm diameter, 4 mm thick flange at one end.",
     "ops": ["Cylinder", "Boolean union", "Boolean cut"]},
    {"name": "L-bracket", "tags": "Sketch · Extrude · Cuts · Pattern",
     "summary": "Two legs at a right angle with slots for adjustment.",
     "prompt": "An L-bracket with two 40 x 30 mm legs, 3 mm thick, and two 6 mm wide slots in each leg.",
     "ops": ["Sketch", "Extrude", "Cut", "Pattern"]},
    {"name": "Hex standoff", "tags": "Polygon sketch · Extrude · Hole",
     "summary": "A hexagonal spacer with a centred hole.",
     "prompt": "A hex standoff, 10 mm across flats, 20 mm tall, with a 3.2 mm hole through the center.",
     "ops": ["Polygon sketch", "Extrude", "Hole"]},
]

VALUES = [
    {"title": "Plain language first",
     "text": "You should be able to describe a part without learning a CAD tool's vocabulary first."},
    {"title": "Verified geometry",
     "text": "Plans are validated for schema and geometry before anything is built, so errors surface early."},
    {"title": "Built to iterate",
     "text": "The output is a starting point. Export it, refine it in your own tools, and come back for the next part."},
]


# ---------- Public pages ----------
def home(request):
    return render(request, "home.html", {"features": FEATURES[:3], "examples": EXAMPLES[:2]})


def about(request):
    return render(request, "about.html", {"values": VALUES})


def features(request):
    return render(request, "features.html", {"features": FEATURES})


def examples(request):
    return render(request, "examples.html", {"examples": EXAMPLES})

def profile(request):
    return render(request,"profile.html",)

def contact(request):
    if request.method == "POST":
        # TODO: save to a model or send an email here (request.POST has the fields)
        messages.success(request, "Thanks! We'll get back to you soon.")
        return redirect("contact")
    return render(request, "contact.html")


# ---------- Try it out ----------
# To require an account for the Try page, add @login_required on try_page and try_generate.
@login_required
def try_page(request):
    return render(request, "try.html", {"examples": EXAMPLES})


@require_POST
def try_generate(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)

    prompt = (body.get("prompt") or "").strip()
    answers = body.get("answers") or None
    if not prompt:
        return JsonResponse({"status": "error", "message": "Please describe the part first."}, status=400)
    if len(prompt) > 2000:
        return JsonResponse({"status": "error", "message": "Prompt is too long (2000 characters max)."}, status=400)

    try:
        result = engine.generate(prompt, answers)
    except Exception as exc:  # surface a friendly error; log the real one
        import logging
        logging.getLogger(__name__).exception("Generation failed: %s", exc)
        return JsonResponse({"status": "error", "message": "Generation failed. Please try again."}, status=500)

    return JsonResponse(result)


# ---------- Auth ----------
def _safe_next(request):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure())
    return nxt if ok else ""


def login_view(request):
    if request.user.is_authenticated:
        return redirect("try")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(_safe_next(request) or "try")
    return render(request, "auth.html", {"form": form, "mode": "login", "next": _safe_next(request)})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("try")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(_safe_next(request) or "try")
    return render(request, "auth.html", {"form": form, "mode": "signup", "next": _safe_next(request)})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")

@login_required
def profile(request):
    p, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "profile.html", {"profile": p})


@login_required
def profile_edit(request):
    p, _ = Profile.objects.get_or_create(user=request.user)
    uform = UserNamesForm(request.POST or None, instance=request.user)
    pform = ProfileForm(request.POST or None, request.FILES or None, instance=p)
    if request.method == "POST" and uform.is_valid() and pform.is_valid():
        uform.save()
        pform.save()
        return redirect("profile")
    return render(request, "profile_edit.html", {"uform": uform, "pform": pform})