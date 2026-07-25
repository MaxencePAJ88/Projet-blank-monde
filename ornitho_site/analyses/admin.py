from django.contrib import admin
from .models import Analyse, BaselineAnalysis


@admin.register(Analyse)
class AnalyseAdmin(admin.ModelAdmin):
	list_display = ("id", "titre", "user", "date_creation")
	search_fields = ("titre", "life_list_file")
	list_filter = ("date_creation",)


@admin.register(BaselineAnalysis)
class BaselineAnalysisAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "date_updated")
	search_fields = ("name",)
