from rest_framework import serializers

from actors.models import Acteur
from users.serializers import UserSerializer

from .models import (
    ActivityItem,
    Narratif,
    PieceJointe,
    SignalComment,
    SignalFavorite,
    SignalReaction,
    Signalement,
    normalize_country_list,
)


class NarratifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Narratif
        fields = ["id", "nom"]


class PieceJointeSerializer(serializers.ModelSerializer):
    fichier_url = serializers.SerializerMethodField()

    class Meta:
        model = PieceJointe
        fields = ["id", "nom_original", "taille", "media_type", "uploaded_at", "fichier_url"]

    def get_fichier_url(self, obj):
        request = self.context.get("request")
        if not obj.fichier:
            return ""
        url = obj.fichier.url
        return request.build_absolute_uri(url) if request else url


class SignalCommentSerializer(serializers.ModelSerializer):
    auteur_detail = UserSerializer(source="auteur", read_only=True)

    class Meta:
        model = SignalComment
        fields = ["id", "contenu", "mentions", "created_at", "auteur_detail"]


class ActivityItemSerializer(serializers.ModelSerializer):
    actor_detail = UserSerializer(source="actor", read_only=True)

    class Meta:
        model = ActivityItem
        fields = ["id", "event_type", "message", "metadata", "created_at", "actor_detail", "signalement_id"]


class SignalementActeurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Acteur
        fields = ["id", "nom", "type_acteur", "score_risque", "pays_operation"]


class SignalementSerializer(serializers.ModelSerializer):
    contributeur_detail = UserSerializer(source="contributeur", read_only=True)
    narratifs_detail = NarratifSerializer(source="narratifs", many=True, read_only=True)
    acteurs_detail = SignalementActeurSerializer(source="acteurs_lies", many=True, read_only=True)
    pieces_jointes = PieceJointeSerializer(many=True, read_only=True)
    commentaires = SignalCommentSerializer(many=True, read_only=True)
    activites = ActivityItemSerializer(many=True, read_only=True)
    criticite_display = serializers.CharField(source="get_criticite_display", read_only=True)
    statut_display = serializers.CharField(source="get_statut_display", read_only=True)
    type_display = serializers.CharField(source="get_type_evenement_display", read_only=True)
    pays_display = serializers.SerializerMethodField()
    reactions_summary = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    my_reactions = serializers.SerializerMethodField()

    class Meta:
        model = Signalement
        fields = "__all__"
        read_only_fields = ["reference", "date_creation", "date_modification", "contributeur", "statut"]

    def get_pays_display(self, obj):
        return obj.pays_display

    def get_reactions_summary(self, obj):
        return {
            reaction: obj.reactions.filter(reaction_type=reaction).count()
            for reaction, _label in SignalReaction.REACTION_TYPES
        }

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and obj.favoris.filter(user=user).exists())

    def get_my_reactions(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return []
        return list(obj.reactions.filter(user=user).values_list("reaction_type", flat=True))


class SignalementCreateSerializer(serializers.ModelSerializer):
    pays = serializers.ListField(child=serializers.CharField(max_length=120), allow_empty=False)

    class Meta:
        model = Signalement
        fields = [
            "titre",
            "pays",
            "date_evenement",
            "type_evenement",
            "criticite",
            "description",
            "narratifs",
            "acteurs_lies",
            "fiabilite",
            "confidentialite",
            "sources_url",
        ]

    def validate_pays(self, value):
        countries = normalize_country_list(value)
        if not countries:
            raise serializers.ValidationError("Au moins un pays est requis.")
        return countries


class SignalCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalComment
        fields = ["contenu", "mentions"]


class SignalReactionSerializer(serializers.Serializer):
    reaction_type = serializers.ChoiceField(choices=[choice[0] for choice in SignalReaction.REACTION_TYPES])


class WorkspaceSerializer(serializers.Serializer):
    stats = serializers.DictField()
    mes_signalements = SignalementSerializer(many=True)
    favoris = SignalementSerializer(many=True)
    activites = ActivityItemSerializer(many=True)
