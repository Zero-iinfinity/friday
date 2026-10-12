from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("features/", views.features, name="features"),
    path("examples/", views.examples, name="examples"),
    path("contact/", views.contact, name="contact"),

    path("try/", views.try_page, name="try"),
    path("try/generate/", views.try_generate, name="try_generate"),

    path("login/", auth_views.LoginView.as_view(template_name = 'views.login_view'), name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", TemplateView.as_view(template_name = 'views.logout_view'), name="logout"),
]
