from django.db import models
from django.contrib.auth.models import User


class Analyse(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    life_list_file = models.FileField(upload_to="life_lists/")
    results_json = models.JSONField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    titre = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.titre or f"Analyse #{self.pk}"


class BaselineAnalysis(models.Model):
    name = models.CharField(max_length=200, unique=True, default="world_baseline")
    baseline_json = models.JSONField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name