from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


User = get_user_model()


class Ressource(models.Model):
    CATS = [
        ("rapports", "Rapports"),
        ("guides", "Guides pratiques"),
        ("outils", "Outils"),
        ("formations", "Formations"),
        ("juridique", "Juridique"),
    ]
    LANGUES = [
        ("fr", "Francais"),
        ("en", "Anglais"),
        ("multi", "Multilingue"),
    ]
    TYPES = [
        ("pdf", "PDF"),
        ("pptx", "PPTX"),
        ("xlsx", "XLSX"),
        ("docx", "DOCX"),
        ("lien", "Lien web"),
    ]
    STATUTS = [
        ("en_attente", "En attente"),
        ("publie", "Publie"),
        ("rejete", "Rejete"),
    ]
    ESPACES = [
        ("hub", "Hub de ressources"),
        ("mou", "MoU US Compact"),
    ]

    titre = models.CharField(max_length=300)
    description = models.TextField()
    categorie = models.CharField(max_length=20, choices=CATS)
    espace = models.CharField(max_length=10, choices=ESPACES, default="hub")
    langue = models.CharField(max_length=10, choices=LANGUES, default="fr")
    type_fichier = models.CharField(max_length=10, choices=TYPES)
    fichier = models.FileField(upload_to="ressources/", null=True, blank=True)
    lien_externe = models.URLField(blank=True)
    pays = models.CharField(max_length=50, blank=True, default="Tous")
    statut = models.CharField(max_length=20, choices=STATUTS, default="en_attente")
    contributeur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="ressources_soumises")
    nb_telechargements = models.PositiveIntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return self.titre

    @property
    def est_nouvelle(self):
        return (timezone.now() - self.date_creation).days <= 30
