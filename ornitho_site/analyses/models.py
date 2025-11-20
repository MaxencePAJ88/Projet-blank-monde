from django.db import models
from django.contrib.auth.models import User


class Analyse(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    life_list_file = models.FileField(upload_to="life_lists/")
    date_creation = models.DateTimeField(auto_now_add=True)
    titre = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.titre or f"Analyse #{self.pk}"