from django.urls import path
from .auth_views import ExploreLoginView, ExploreLogoutView, register

urlpatterns = [
    path("login/", ExploreLoginView.as_view(), name="login"),
    path("register/", register, name="register"),
    path("logout/", ExploreLogoutView.as_view(), name="logout"),
]