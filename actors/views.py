import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Acteur, Connexion
from .serializers import ActeurSerializer, ConnexionSerializer


User = get_user_model()


def is_platform_admin(user):
    return bool(
        user
        and user.is_authenticated
        and str(user.email).strip().lower() == settings.DEMO_ADMIN_EMAIL.strip().lower()
    )


def _normalize_actor_payload(request):
    data = request.data.copy()
    if hasattr(data, "getlist"):
        countries = [item.strip() for item in data.getlist("pays_operation") if str(item).strip()]
        if not countries:
            raw_value = data.get("pays_operation")
            if isinstance(raw_value, str) and raw_value.strip():
                try:
                    parsed = json.loads(raw_value)
                    if isinstance(parsed, list):
                        countries = [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    countries = [item.strip() for item in raw_value.split(",") if item.strip()]
        data.setlist("pays_operation", countries)
        return data

    countries = data.get("pays_operation", [])
    if isinstance(countries, str):
        try:
            parsed = json.loads(countries)
            countries = parsed if isinstance(parsed, list) else [countries]
        except json.JSONDecodeError:
            countries = [item.strip() for item in countries.split(",") if item.strip()]
    data["pays_operation"] = [str(item).strip() for item in countries if str(item).strip()]
    return data


def ensure_demo_actors():
    demo_user = User.objects.filter(email__iexact=settings.DEMO_ADMIN_EMAIL, is_active=True).first()
    if not demo_user:
        return
    from .seed_data import get_seed_actor_names, sync_seed_acteurs

    expected_names = set(get_seed_actor_names())
    current_names = set(
        Acteur.objects.filter(contribue_par=demo_user).values_list("nom", flat=True)
    )
    if current_names != expected_names:
        sync_seed_acteurs(demo_user)


def _country_matches(acteur, country):
    if not country:
        return True
    return country in (acteur.pays_operation or [])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_acteurs(request):
    ensure_demo_actors()
    queryset = Acteur.objects.all()
    if request.query_params.get("type"):
        queryset = queryset.filter(type_acteur=request.query_params["type"])
    country = request.query_params.get("pays")
    if country:
        queryset = [acteur for acteur in queryset if _country_matches(acteur, country)]
    return Response(ActeurSerializer(queryset, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_acteur(request):
    ensure_demo_actors()
    if not is_platform_admin(request.user):
        return Response({"error": "Permission insuffisante."}, status=403)
    serializer = ActeurSerializer(data=_normalize_actor_payload(request))
    if serializer.is_valid():
        acteur = serializer.save(contribue_par=request.user)
        return Response(ActeurSerializer(acteur).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def detail_acteur(request, pk):
    ensure_demo_actors()
    try:
        acteur = Acteur.objects.get(pk=pk)
        if request.method == "GET":
            return Response(ActeurSerializer(acteur).data)
        if not is_platform_admin(request.user):
            return Response({"error": "Permission insuffisante."}, status=403)
        serializer = ActeurSerializer(acteur, data=_normalize_actor_payload(request), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    except Acteur.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def network_data(request):
    ensure_demo_actors()
    acteurs = Acteur.objects.all()
    if request.query_params.get("type"):
        acteurs = acteurs.filter(type_acteur=request.query_params["type"])
    country = request.query_params.get("pays")
    if country:
        acteurs = [acteur for acteur in acteurs if _country_matches(acteur, country)]
    acteurs = list(acteurs)
    visible_ids = {acteur.id for acteur in acteurs}
    connexions = Connexion.objects.select_related("source", "cible").all()
    connexions = [connexion for connexion in connexions if connexion.source_id in visible_ids and connexion.cible_id in visible_ids]
    return Response(
        {
            "nodes": [
                {
                    "id": acteur.id,
                    "nom": acteur.nom,
                    "type": acteur.type_acteur,
                    "score": acteur.score_risque,
                    "pays": acteur.pays_operation,
                }
                for acteur in acteurs
            ],
            "edges": [{"source": connexion.source_id, "cible": connexion.cible_id, "type": connexion.type_lien} for connexion in connexions],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_acteur_profile(request, pk):
    ensure_demo_actors()
    try:
        acteur = Acteur.objects.get(pk=pk)
    except Acteur.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)

    payload = {
        "id": acteur.id,
        "nom": acteur.nom,
        "type_acteur": acteur.type_acteur,
        "pays_operation": acteur.pays_operation,
        "logo_url": request.build_absolute_uri(acteur.logo.url) if acteur.logo else "",
        "photo_url": request.build_absolute_uri(acteur.photo.url) if acteur.photo else "",
        "score_risque": acteur.score_risque,
        "sources_financement": acteur.sources_financement,
        "zone_influence": acteur.zone_influence,
        "strategie_mode_operatoire": acteur.strategie_mode_operatoire,
        "discours_messages_cles": acteur.discours_messages_cles,
        "description": acteur.description,
        "narratifs": list(acteur.narratifs.values_list("nom", flat=True)),
        "date_creation": acteur.date_creation.isoformat(),
        "date_modification": acteur.date_modification.isoformat(),
    }
    response = HttpResponse(
        json.dumps(payload, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="acteur-{acteur.id}.json"'
    return response
