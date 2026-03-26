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
    if Acteur.objects.exists():
        return

    from signals.models import Narratif, Signalement

    demo_user = User.objects.filter(email__iexact=settings.DEMO_ADMIN_EMAIL, is_active=True).first()
    if not demo_user:
        return

    narratifs = {
        "Protection de la famille": Narratif.objects.get_or_create(nom="Protection de la famille")[0],
        "Anti-IVG": Narratif.objects.get_or_create(nom="Anti-IVG")[0],
        "Religion et morale": Narratif.objects.get_or_create(nom="Religion et morale")[0],
        "Agenda occidental": Narratif.objects.get_or_create(nom="Agenda occidental")[0],
        "Valeurs religieuses": Narratif.objects.get_or_create(nom="Valeurs religieuses")[0],
    }

    dataset = [
        {
            "nom": "Alliance pour la Famille Cameroun",
            "type_acteur": "local",
            "pays_operation": ["Cameroun"],
            "score_risque": 78,
            "sources_financement": "Collectes locales, relais confessionnels, soutiens prives.",
            "zone_influence": "Parlement, eglises, medias communautaires.",
            "strategie_mode_operatoire": "Lobbying legislatif, petitions, campagnes publiques.",
            "discours_messages_cles": "Protection de la famille, refus des droits sexuels et reproductifs.",
            "description": "Coalition locale active dans le plaidoyer anti-droits au Cameroun.",
            "narratifs": ["Protection de la famille", "Anti-IVG"],
        },
        {
            "nom": "Radio Esperance Afrique",
            "type_acteur": "media",
            "pays_operation": ["Mali", "Benin"],
            "score_risque": 62,
            "sources_financement": "Sponsors locaux, reseaux religieux, espaces publicitaires militants.",
            "zone_influence": "Stations radio, debats publics, auditoires ruraux.",
            "strategie_mode_operatoire": "Emission en serie, amplification de rumeurs, tribunes d'opinion.",
            "discours_messages_cles": "Agenda occidental, corruption morale, defense des traditions.",
            "description": "Media de relais regional pour des narratifs anti-droits.",
            "narratifs": ["Agenda occidental", "Religion et morale"],
        },
        {
            "nom": "Coalition Foi et Nation",
            "type_acteur": "rel",
            "pays_operation": ["RCA", "Madagascar"],
            "score_risque": 71,
            "sources_financement": "Reseaux confessionnels regionaux, donations internationales.",
            "zone_influence": "Eglises, marches, responsables communautaires.",
            "strategie_mode_operatoire": "Predications, mobilisations communautaires, declarations publiques.",
            "discours_messages_cles": "Valeurs religieuses, moralite publique, souverainete culturelle.",
            "description": "Reseau religieux mobilise contre plusieurs agendas SRHR.",
            "narratifs": ["Valeurs religieuses", "Religion et morale"],
        },
        {
            "nom": "Family Watch International",
            "type_acteur": "intl",
            "pays_operation": ["Etats-Unis", "Cameroun", "RCA", "Madagascar"],
            "score_risque": 88,
            "sources_financement": "Fondations conservatrices, partenaires internationaux.",
            "zone_influence": "ONU, ministeres, reseaux parlementaires, conferences internationales.",
            "strategie_mode_operatoire": "Partenariats, production de contenu, influence institutionnelle.",
            "discours_messages_cles": "Protection des enfants, anti-genre, anti-IVG.",
            "description": "Acteur international de reference dans la diffusion de narratifs anti-droits.",
            "narratifs": ["Protection de la famille", "Anti-IVG", "Agenda occidental"],
        },
    ]

    created = {}
    for item in dataset:
        narratif_names = item.pop("narratifs")
        acteur = Acteur.objects.create(contribue_par=demo_user, **item)
        acteur.narratifs.set([narratifs[name] for name in narratif_names])
        created[acteur.nom] = acteur

    connexions = [
        ("Family Watch International", "Alliance pour la Famille Cameroun", "financement", "Soutien strategique et mise en reseau."),
        ("Family Watch International", "Coalition Foi et Nation", "partenaire", "Coordination de campagnes et de messages."),
        ("Radio Esperance Afrique", "Alliance pour la Famille Cameroun", "media", "Relais des prises de position et campagnes."),
    ]
    for source_name, cible_name, type_lien, description in connexions:
        Connexion.objects.get_or_create(
            source=created[source_name],
            cible=created[cible_name],
            type_lien=type_lien,
            defaults={"description": description},
        )

    signal_map = {
        "Projet de loi anti-SRHR au Cameroun": ["Alliance pour la Famille Cameroun", "Family Watch International"],
        "Campagne mediatique contre les ONG SRHR au Mali": ["Radio Esperance Afrique"],
        "Lobbying legislatif anti-LGBTIQ+ en RCA": ["Coalition Foi et Nation", "Family Watch International"],
        "Petition contre le Protocole de Maputo a Madagascar": ["Coalition Foi et Nation", "Family Watch International"],
    }
    for signalement in Signalement.objects.all():
        actor_names = signal_map.get(signalement.titre, [])
        if actor_names:
            signalement.acteurs_lies.set([created[name] for name in actor_names])


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
