from django.urls import path
from . import views

app_name = "analyses"

urlpatterns = [
    path("upload/", views.upload_life_list_view, name="upload"),
    path("<int:analyse_id>/", views.detail_analyse_view, name="detail"),
]