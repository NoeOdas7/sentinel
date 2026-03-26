from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

User = get_user_model()

COUNTRY_CODE_LABELS = {
    "benin": "Benin",
    "cameroun": "Cameroun",
    "cote_ivoire": "Cote d'Ivoire",
    "guinee": "Guinee",
    "madagascar": "Madagascar",
    "mali": "Mali",
    "rca": "RCA",
}


def normalize_country_name(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return COUNTRY_CODE_LABELS.get(text.lower(), text)


def normalize_country_list(value):
    if isinstance(value, list):
        raw_items = value
    elif value in (None, ""):
        raw_items = []
    else:
        raw_items = [value]

    countries = []
    seen = set()
    for item in raw_items:
        label = normalize_country_name(item)
        lowered = label.lower()
        if not label or lowered in seen:
            continue
        countries.append(label)
        seen.add(lowered)
    return countries


class Narratif(models.Model):
    nom = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Signalement(models.Model):
    TYPES = [
        ("legislatif", "Legislatif"),
        ("medias", "Medias"),
        ("religieux", "Religieux"),
        ("ong", "ONG"),
        ("numerique", "Numerique"),
        ("autre", "Autre"),
    ]
    CRITICITES = [("faible", "Faible"), ("moderee", "Moderee"), ("elevee", "Elevee")]
    STATUTS = [("brouillon", "Brouillon"), ("en_attente", "En attente"), ("valide", "Valide"), ("rejete", "Rejete")]
    FIABILITES = [("confirmee", "Confirmee"), ("probable", "Probable"), ("rumeur", "Rumeur")]
    CONFIS = [("membres", "Public membres"), ("moderateurs", "Moderateurs"), ("staff", "Staff ODAS")]
    reference = models.CharField(max_length=20, unique=True, editable=False)
    titre = models.CharField(max_length=300)
    pays = models.JSONField(default=list, blank=True)
    date_evenement = models.DateField()
    type_evenement = models.CharField(max_length=20, choices=TYPES)
    criticite = models.CharField(max_length=10, choices=CRITICITES)
    description = models.TextField()
    narratifs = models.ManyToManyField(Narratif, blank=True, related_name="signalements")
    acteurs_lies = models.ManyToManyField("actors.Acteur", blank=True, related_name="signalements")
    fiabilite = models.CharField(max_length=20, choices=FIABILITES, blank=True)
    confidentialite = models.CharField(max_length=20, choices=CONFIS, default="membres")
    statut = models.CharField(max_length=20, choices=STATUTS, default="en_attente")
    contributeur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sig_crees")
    validateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sig_valides")
    motif_rejet = models.TextField(blank=True)
    sources_url = models.JSONField(default=list, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.reference} - {self.titre}"

    @property
    def pays_list(self):
        return normalize_country_list(self.pays)

    @property
    def pays_display(self):
        return ", ".join(self.pays_list)

    @property
    def pays_primary(self):
        countries = self.pays_list
        return countries[0] if countries else ""

    def save(self, *args, **kwargs):
        self.pays = self.pays_list
        if not self.reference:
            year = timezone.now().year
            count = Signalement.objects.filter(date_creation__year=year).count() + 1
            self.reference = f"SIG-{year}-{count:04d}"
        super().save(*args, **kwargs)


class PieceJointe(models.Model):
    MEDIA_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
        ("pdf", "PDF"),
        ("document", "Document"),
        ("autre", "Autre"),
    ]

    signalement = models.ForeignKey(Signalement, on_delete=models.CASCADE, related_name="pieces_jointes")
    fichier = models.FileField(upload_to="signalements/")
    nom_original = models.CharField(max_length=255)
    taille = models.PositiveBigIntegerField()
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES, default="autre")
    uploaded_at = models.DateTimeField(auto_now_add=True)


class SignalComment(models.Model):
    signalement = models.ForeignKey(Signalement, on_delete=models.CASCADE, related_name="commentaires")
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="signal_comments")
    contenu = models.TextField()
    mentions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class SignalReaction(models.Model):
    REACTION_TYPES = [
        ("utile", "Utile"),
        ("a_verifier", "A verifier"),
        ("prioritaire", "Prioritaire"),
    ]

    signalement = models.ForeignKey(Signalement, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="signal_reactions")
    reaction_type = models.CharField(max_length=20, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["signalement", "user", "reaction_type"], name="unique_signal_reaction")
        ]


class SignalFavorite(models.Model):
    signalement = models.ForeignKey(Signalement, on_delete=models.CASCADE, related_name="favoris")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="signal_favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["signalement", "user"], name="unique_signal_favorite")
        ]


class ActivityItem(models.Model):
    EVENT_TYPES = [
        ("creation", "Creation"),
        ("validation", "Validation"),
        ("rejet", "Rejet"),
        ("commentaire", "Commentaire"),
        ("reaction", "Reaction"),
        ("favori", "Favori"),
        ("ressource", "Ressource"),
    ]

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    signalement = models.ForeignKey(Signalement, on_delete=models.CASCADE, null=True, blank=True, related_name="activities")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    message = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
