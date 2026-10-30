import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .auth_forms import LoginForm, RegisterForm


def show_main(request):
    return render(request, "index.html")


def _safe_next(request):
    """Return the requested `next` URL only if it points back to this site."""
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return ''


@require_http_methods(["GET", "POST"])
def register(request):
    next_url = _safe_next(request)
    if request.user.is_authenticated:
        return redirect(next_url or "show_main")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Account created. Log in as {user.username} to start your garden.")
        login_url = reverse("login")
        return redirect(f"{login_url}?{urlencode({'next': next_url})}" if next_url else login_url)

    context = {"form": form, "next": next_url}
    return render(request, "register.html", context, status=400 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
def login_user(request):
    next_url = _safe_next(request)
    if request.user.is_authenticated:
        return redirect(next_url or "show_main")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Welcome back, {user.username}.")
        response = redirect(next_url or "show_main")
        response.set_cookie('last_login', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return response

    context = {"form": form, "next": next_url}
    return render(request, "login.html", context, status=400 if request.method == "POST" else 200)


@require_POST
def logout_user(request):
    logout(request)
    messages.info(request, "You have been logged out. See you in the garden soon.")
    response = redirect("show_main")
    response.delete_cookie('last_login')
    return response
