from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "analyses"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("upload/", views.upload_life_list_view, name="upload"),
    path("baseline/refresh/", views.refresh_baseline_view, name="refresh_baseline"),
    path("my-analyses/", views.user_analyses_view, name="user_analyses"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="analyses/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="analyses:home"), name="logout"),
    path("accounts/register/", views.register_view, name="register"),
    path("<int:analyse_id>/", views.detail_analyse_view, name="detail"),
    path("<int:analyse_id>/section/blanks/", views.section_blanks_json, name="section_blanks_json"),
    path("<int:analyse_id>/section/blanks/by-country/", views.section_blanks_by_country_json, name="section_blanks_by_country_json"),
    path("<int:analyse_id>/section/summary/", views.section_summary_json, name="section_summary_json"),
    path("baseline/section/blanks/", views.baseline_section_blanks_json, name="baseline_section_blanks_json"),
    path("baseline/section/blanks/by-country/", views.baseline_section_blanks_by_country_json, name="baseline_section_blanks_by_country_json"),
    path("baseline/section/summary/", views.baseline_section_summary_json, name="baseline_section_summary_json"),
]