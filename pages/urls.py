from django.urls import path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("features/", views.features, name="features"),
    path("examples/", views.examples, name="examples"),
    path("contact/", views.contact, name="contact"),
    path("profile/",views.profile,name = "profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),

    path("try/", views.try_page, name="try"),
    path("try/generate/", views.try_generate, name="try_generate"),

    # FIX: Point directly to the custom views you wrote in views.py
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),

]