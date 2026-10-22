from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render
import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import GardenJournalEntry
from .forms import GardenJournalEntryForm


def show_main(request):
    return render(request, "index.html")

def register(request):
    form = UserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Akun berhasil dibuat. Silakan login.")
        return redirect("login")

    context = {
        "name": "Burhan",
        "form": form,
    }
    return render(request, "register.html", context)

def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        response = redirect("show_main")
        response.set_cookie('last_login', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return response

    context = {
        "name": "Burhan",
        "form": form,
    }
    return render(request, "login.html", context)

def logout_user(request):
    logout(request)
    response = redirect("show_main")
    response.delete_cookie('last_login')
    return response

# Garden Journal

@login_required
def garden_journal(request):
    entries = GardenJournalEntry.objects.filter(
        user=request.user
    )

    return render(
        request,
        "garden_journal.html",
        {"entries": entries},
    )


@login_required
def garden_journal_create(request):
    if request.method == "POST":
        form = GardenJournalEntryForm(request.POST)

        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()

            messages.success(
                request,
                "Catatan jurnal berhasil ditambahkan.",
            )
            return redirect("garden_journal")
    else:
        form = GardenJournalEntryForm()

    return render(
        request,
        "garden_journal_form.html",
        {
            "form": form,
            "page_title": "Add Journal Entry",
        },
    )


@login_required
def garden_journal_edit(request, entry_id):
    entry = get_object_or_404(
        GardenJournalEntry,
        pk=entry_id,
        user=request.user,
    )

    if request.method == "POST":
        form = GardenJournalEntryForm(
            request.POST,
            instance=entry,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Catatan jurnal berhasil diperbarui.",
            )
            return redirect("garden_journal")
    else:
        form = GardenJournalEntryForm(instance=entry)

    return render(
        request,
        "garden_journal_form.html",
        {
            "form": form,
            "page_title": "Edit Catatan Jurnal",
        },
    )


@login_required
def garden_journal_delete(request, entry_id):
    entry = get_object_or_404(
        GardenJournalEntry,
        pk=entry_id,
        user=request.user,
    )

    if request.method == "POST":
        entry.delete()
        messages.success(
            request,
            "Catatan jurnal berhasil dihapus.",
        )
        return redirect("garden_journal")

    return render(
        request,
        "garden_journal_confirm_delete.html",
        {"entry": entry},
    )


