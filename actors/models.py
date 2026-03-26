from django.contrib.auth import get_user_model
from django.db import models
from simple_history.models import HistoricalRecords


User = get_user_model()


class Acteur(models.Model):
    TYPES = [
        ("intl", "International"),
        ("local", "Local/National"),
        ("media", "Medias"),
        ("rel", "Religieux"),
    ]

    nom = models.CharField(max_length=300, unique=True)
    type_acteur = models.CharField(max_length=10, choices=TYPES)
    pays_operation = models.JSONField(default=list)
    logo = models.FileField(upload_to="acteurs/logos/", null=True, blank=True)
    photo = models.FileField(upload_to="acteurs/photos/", null=True, blank=True)
    score_risque = models.IntegerField(default=0)
    sources_financement = models.TextField(blank=True)
    zone_influence = models.TextField(blank=True)
    strategie_mode_operatoire = models.TextField(blank=True)
    discours_messages_cles = models.TextField(blank=True)
    description = models.TextField(blank=True)
    narratifs = models.ManyToManyField("signals.Narratif", blank=True)
    contribue_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="acteurs_crees")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-score_risque"]

    def __str__(self):
        return self.nom


class Connexion(models.Model):
    TYPES = [
        ("financement", "Financement"),
        ("partenaire", "Partenariat"),
        ("media", "Relais mediatique"),
    ]

    source = models.ForeignKey(Acteur, on_delete=models.CASCADE, related_name="connexions_sortantes")
    cible = models.ForeignKey(Acteur, on_delete=models.CASCADE, related_name="connexions_entrantes")
    type_lien = models.CharField(max_length=20, choices=TYPES)
    description = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["source", "cible", "type_lien"]

    def __str__(self):
        return f"{self.source} -> {self.cible}"
