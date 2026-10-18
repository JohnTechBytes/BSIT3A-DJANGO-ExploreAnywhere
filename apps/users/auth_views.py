from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .auth_forms import ExploreRegistrationForm


class ExploreLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
       return str(reverse_lazy("hobbies:select"))


class ExploreLogoutView(LogoutView):
    next_page = "/"


def register(request):
    if request.user.is_authenticated:
        return redirect("hobbies:select")

    form = ExploreRegistrationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("hobbies:select")

    return render(
        request,
        "registration/register.html",
        {"form": form},
    )
