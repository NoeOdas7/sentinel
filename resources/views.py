from django.conf import settings
from django.db.models import Q
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Ressource
from .serializers import RessourceSerializer


def is_platform_admin(user):
    return bool(
        user
        and user.is_authenticated
        and str(user.email).strip().lower() == settings.DEMO_ADMIN_EMAIL.strip().lower()
    )


def ensure_demo_mou_resources():
    if Ressource.objects.filter(espace="mou").exists():
        return

    dataset = [
        {
            "titre": "MoU US Compact - Cadre regional 2026",
            "description": "Memorandum cadre pour la coordination regionale, les livrables et la gouvernance documentaire.",
            "categorie": "rapports",
            "espace": "mou",
            "langue": "en",
            "type_fichier": "pdf",
            "lien_externe": "https://example.org/mou-us-compact-cadre",
            "pays": "Regional",
            "statut": "publie",
        },
        {
            "titre": "Annexes juridiques - US Compact",
            "description": "Compilation des annexes juridiques, clauses de suivi et dispositifs de conformite.",
            "categorie": "juridique",
            "espace": "mou",
            "langue": "fr",
            "type_fichier": "docx",
            "lien_externe": "https://example.org/mou-us-compact-annexes",
            "pays": "Tous",
            "statut": "publie",
        },
        {
            "titre": "Tableau de suivi financier - Compact",
            "description": "Tableau de reference pour les engagements, couts et jalons budgetaires du programme.",
            "categorie": "outils",
            "espace": "mou",
            "langue": "fr",
            "type_fichier": "xlsx",
            "lien_externe": "https://example.org/mou-us-compact-finance",
            "pays": "Tous",
            "statut": "publie",
        },
    ]
    for item in dataset:
        Ressource.objects.get_or_create(
            titre=item["titre"],
            espace="mou",
            defaults=item,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_ressources(request):
    ensure_demo_mou_resources()
    qs = Ressource.objects.filter(statut="publie")
    espace = request.query_params.get("espace")
    if espace in {"hub", "mou"}:
        qs = qs.filter(espace=espace)
    if request.query_params.get("cat"):
        qs = qs.filter(categorie=request.query_params["cat"])
    if request.query_params.get("pays"):
        qs = qs.filter(pays=request.query_params["pays"])
    if request.query_params.get("langue"):
        qs = qs.filter(langue=request.query_params["langue"])
    q = request.query_params.get("q")
    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(description__icontains=q)).distinct()
    return Response(RessourceSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_ressource(request):
    serializer = RessourceSerializer(data=request.data)
    if serializer.is_valid():
        status_value = "publie" if is_platform_admin(request.user) else "en_attente"
        resource = serializer.save(contributeur=request.user, statut=status_value)
        return Response(RessourceSerializer(resource).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def valider_ressource(request, pk):
    if not is_platform_admin(request.user):
        return Response({"error": "Permission insuffisante."}, status=403)
    try:
        resource = Ressource.objects.get(pk=pk)
        resource.statut = "publie" if request.data.get("action", "publie") == "valider" else "rejete"
        resource.save()
        return Response(RessourceSerializer(resource).data)
    except Ressource.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)
