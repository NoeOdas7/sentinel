import csv
import io
from pathlib import Path
from datetime import date, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.http import QueryDict
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
from .serializers import (
    ActivityItemSerializer,
    NarratifSerializer,
    SignalCommentCreateSerializer,
    SignalCommentSerializer,
    SignalReactionSerializer,
    SignalementCreateSerializer,
    SignalementSerializer,
)

User = get_user_model()


def is_platform_admin(user):
    return bool(
        user
        and user.is_authenticated
        and str(user.email).strip().lower() == settings.DEMO_ADMIN_EMAIL.strip().lower()
    )


def signalement_countries(signalement):
    return normalize_country_list(getattr(signalement, "pays", []))


def signalement_matches_country(signalement, countries):
    if not countries:
        return True
    visible = {item.lower() for item in signalement_countries(signalement)}
    expected = {item.lower() for item in countries if item}
    return bool(visible & expected)


def filter_signalements_queryset(queryset, request):
    qs = queryset
    for param, field in [("criticite", "criticite"), ("type", "type_evenement"), ("statut", "statut")]:
        if request.query_params.get(param):
            qs = qs.filter(**{field: request.query_params[param]})

    actor_ids = []
    raw_actor_ids = request.query_params.get("acteur") or request.query_params.get("acteurs") or ""
    for value in str(raw_actor_ids).split(","):
        value = value.strip()
        if value.isdigit():
            actor_ids.append(int(value))
    if actor_ids:
        qs = qs.filter(acteurs_lies__id__in=actor_ids).distinct()
    return qs


def parse_report_dates(request):
    month_value = (request.query_params.get("month") or "").strip()
    start_value = (request.query_params.get("start_date") or "").strip()
    end_value = (request.query_params.get("end_date") or "").strip()

    if month_value:
        try:
            current = datetime.strptime(month_value, "%Y-%m").date()
        except ValueError as exc:
            raise ValueError("Le mois doit etre au format YYYY-MM.") from exc
        next_month = date(current.year + (1 if current.month == 12 else 0), 1 if current.month == 12 else current.month + 1, 1)
        return current, next_month

    if start_value and end_value:
        try:
            start_date = datetime.strptime(start_value, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("Les dates doivent etre au format YYYY-MM-DD.") from exc
        if end_date < start_date:
            raise ValueError("La date de fin doit etre posterieure a la date de debut.")
        return start_date, end_date

    return None, None


def detect_media_type(filename):
    ext = Path(filename).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return "image"
    if ext in {".mp4", ".mov", ".webm", ".avi"}:
        return "video"
    if ext == ".pdf":
        return "pdf"
    if ext in {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt"}:
        return "document"
    return "autre"


def record_activity(event_type, message, actor=None, signalement=None, **metadata):
    return ActivityItem.objects.create(
        actor=actor,
        signalement=signalement,
        event_type=event_type,
        message=message,
        metadata=metadata or {},
    )


def ensure_demo_media(signalement, index):
    if signalement.pieces_jointes.exists():
        return
    palette = [
        ("#17324d", "#1fb89f", "#f6c667"),
        ("#1d2440", "#ff7d6d", "#f4c857"),
        ("#143d35", "#20c997", "#8bd3dd"),
        ("#241b36", "#9f7aea", "#ffb86c"),
    ]
    bg, accent, glow = palette[index % len(palette)]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1440" viewBox="0 0 1280 1440">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{bg}"/>
    <stop offset="100%" stop-color="#090c14"/>
  </linearGradient>
  <radialGradient id="halo" cx="0.18" cy="0.16" r="0.9">
    <stop offset="0%" stop-color="{accent}" stop-opacity="0.95"/>
    <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect width="1280" height="1440" fill="url(#bg)"/>
<rect width="1280" height="1440" fill="url(#halo)"/>
<circle cx="1080" cy="240" r="180" fill="{glow}" fill-opacity="0.16"/>
<rect x="94" y="118" width="1092" height="1204" rx="48" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.12)"/>
<text x="130" y="230" fill="#f3efe8" font-family="Arial, Helvetica, sans-serif" font-size="58" font-weight="700">SENTINEL REPORT</text>
<text x="130" y="308" fill="{glow}" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700">{signalement.pays_display.upper()} • {signalement.get_type_evenement_display().upper()}</text>
<text x="130" y="416" fill="#ffffff" font-family="Arial, Helvetica, sans-serif" font-size="84" font-weight="800">{signalement.titre[:28]}</text>
<text x="130" y="492" fill="#ffffff" font-family="Arial, Helvetica, sans-serif" font-size="84" font-weight="800">{signalement.titre[28:56]}</text>
<text x="130" y="626" fill="#dbe7f2" font-family="Arial, Helvetica, sans-serif" font-size="34">{signalement.reference} • CRITICITE {signalement.get_criticite_display().upper()}</text>
<rect x="130" y="700" width="1020" height="2" fill="rgba(255,255,255,0.16)"/>
<text x="130" y="808" fill="#d5dde8" font-family="Arial, Helvetica, sans-serif" font-size="36">{signalement.description[:88]}</text>
<text x="130" y="860" fill="#d5dde8" font-family="Arial, Helvetica, sans-serif" font-size="36">{signalement.description[88:176]}</text>
<text x="130" y="1260" fill="{accent}" font-family="Arial, Helvetica, sans-serif" font-size="28" font-weight="700">Reseau ferme ODAS • veille collaborative</text>
</svg>"""
    filename = f"demo-visual-{signalement.reference.lower()}.svg"
    piece = PieceJointe(
        signalement=signalement,
        nom_original=filename,
        taille=len(svg.encode("utf-8")),
        media_type="image",
    )
    piece.fichier.save(f"signalements/{filename}", ContentFile(svg.encode("utf-8")), save=True)


def backfill_demo_social_content(demo_user):
    signalements = list(Signalement.objects.select_related("contributeur").order_by("-date_evenement")[:6])
    if not signalements:
        return

    voices = [demo_user]
    comment_templates = [
        "Veille complementaire en cours. Plusieurs relais communautaires reprennent deja ce cadrage.",
        "Point de contexte ajoute: le narratif circule aussi dans des groupes WhatsApp locaux.",
        "A surveiller cette semaine, surtout si le sujet remonte cote radio ou parlement.",
    ]
    validation_messages = [
        "Diffuse au reseau de veille pour verification terrain.",
        "Piece de contexte ajoutee pour l'equipe editorial.",
        "Publication recommandee dans le flux prioritaire.",
    ]

    for index, signalement in enumerate(signalements):
        ensure_demo_media(signalement, index)

        if signalement.statut == "valide" and not signalement.favoris.exists():
            SignalFavorite.objects.get_or_create(signalement=signalement, user=demo_user)

        reaction_user = voices[index % len(voices)]
        reaction_type = SignalReaction.REACTION_TYPES[index % len(SignalReaction.REACTION_TYPES)][0]
        SignalReaction.objects.get_or_create(signalement=signalement, user=reaction_user, reaction_type=reaction_type)

        if not signalement.commentaires.exists():
            SignalComment.objects.create(
                signalement=signalement,
                auteur=voices[(index + 1) % len(voices)],
                contenu=comment_templates[index % len(comment_templates)],
                mentions=[demo_user.email] if demo_user.email else [],
            )

        existing_messages = set(signalement.activities.values_list("message", flat=True))
        social_messages = [
            (demo_user, "ressource", validation_messages[index % len(validation_messages)]),
            (voices[index % len(voices)], "commentaire", f"Discussion interne activee sur {signalement.reference}"),
        ]
        for actor, event_type, message in social_messages:
            if message not in existing_messages:
                record_activity(event_type, message, actor=actor, signalement=signalement, source="demo")


def ensure_demo_signalements():
    demo_user = User.objects.filter(email__iexact=settings.DEMO_ADMIN_EMAIL, is_active=True).first()
    if not demo_user:
        demo_user = User.objects.create_user(
            email="admin@odas.org",
            password="admin123",
            nom_complet="Admin Demo ODAS",
            role="admin",
            pays="regional",
            is_active=True,
            is_approved=True,
            is_staff=True,
            is_superuser=True,
            approval_status="approved",
            first_login_completed=True,
        )

    if Signalement.objects.exists():
        backfill_demo_social_content(demo_user)
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
            "titre": "Projet de loi anti-SRHR au Cameroun",
        "pays": ["Cameroun"],
            "date_evenement": "2026-03-10",
            "type_evenement": "legislatif",
            "criticite": "elevee",
            "description": "Un projet de loi visant a criminaliser l'assistance a l'avortement a ete depose a l'Assemblee nationale du Cameroun.",
            "fiabilite": "confirmee",
            "statut": "valide",
            "narratifs": ["Protection de la famille", "Anti-IVG"],
        },
        {
            "titre": "Campagne mediatique contre les ONG SRHR au Mali",
        "pays": ["Mali"],
            "date_evenement": "2026-03-08",
            "type_evenement": "medias",
            "criticite": "moderee",
            "description": "Une serie d'emissions radio accuse des ONG internationales de promouvoir l'avortement au Mali.",
            "fiabilite": "probable",
            "statut": "valide",
            "narratifs": ["Agenda occidental"],
        },
        {
            "titre": "Lobbying legislatif anti-LGBTIQ+ en RCA",
        "pays": ["RCA"],
            "date_evenement": "2026-03-18",
            "type_evenement": "legislatif",
            "criticite": "elevee",
            "description": "Un projet de loi criminalisant les relations entre personnes de meme sexe a ete soumis au Parlement centrafricain.",
            "fiabilite": "confirmee",
            "statut": "en_attente",
            "narratifs": ["Religion et morale"],
        },
        {
            "titre": "Campagne numerique contre l'education sexuelle au Benin",
        "pays": ["Benin"],
            "date_evenement": "2026-03-20",
            "type_evenement": "numerique",
            "criticite": "moderee",
            "description": "Une campagne de desinformation sur les reseaux sociaux cible le programme d'education sexuelle des lycees beninois.",
            "fiabilite": "probable",
            "statut": "en_attente",
            "narratifs": ["Protection de la famille"],
        },
        {
            "titre": "Petition contre le Protocole de Maputo a Madagascar",
        "pays": ["Madagascar"],
            "date_evenement": "2026-03-21",
            "type_evenement": "ong",
            "criticite": "elevee",
            "description": "Une coalition d'ONG religieuses a lance une petition nationale exigeant le retrait de Madagascar du Protocole de Maputo.",
            "fiabilite": "confirmee",
            "statut": "en_attente",
            "narratifs": ["Valeurs religieuses"],
        },
    ]

    created_signals = []
    for item in dataset:
        tags = item.pop("narratifs")
        status = item.pop("statut")
        sig = Signalement.objects.create(
            contributeur=demo_user,
            validateur=demo_user if status in ["valide", "rejete"] else None,
            date_validation=timezone.now() if status in ["valide", "rejete"] else None,
            statut=status,
            **item,
        )
        sig.narratifs.set([narratifs[name] for name in tags])
        created_signals.append(sig)

    for sig in created_signals:
        record_activity(
            "validation" if sig.statut == "valide" else "creation",
            f"{sig.reference} a ete {'valide' if sig.statut == 'valide' else 'soumis'}",
            actor=demo_user,
            signalement=sig,
            statut=sig.statut,
        )
    backfill_demo_social_content(demo_user)


def visible_signalements_for(user):
    if is_platform_admin(user):
        return Signalement.objects.all()
    return Signalement.objects.filter(Q(statut="valide") | Q(contributeur=user)).distinct()


def serialize_signalements(queryset, request):
    return SignalementSerializer(queryset[:50], many=True, context={"request": request}).data


def normalize_signalement_payload(request):
    payload = {}
    if isinstance(request.data, QueryDict):
        payload.update(request.data.dict())
    else:
        payload.update(request.data)

    payload["pays"] = [item for item in request.data.getlist("pays") if item]
    payload["sources_url"] = [item for item in request.data.getlist("sources_url") if item]
    payload["narratifs"] = [item for item in request.data.getlist("narratifs") if item]
    payload["acteurs_lies"] = [item for item in request.data.getlist("acteurs_lies") if item]
    return payload


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_signalements(request):
    ensure_demo_signalements()
    qs = visible_signalements_for(request.user)
    if request.query_params.get("mine") == "true":
        qs = qs.filter(contributeur=request.user)
    qs = filter_signalements_queryset(qs, request)
    countries = normalize_country_list(
        [item for item in (request.query_params.get("pays") or "").split(",") if item.strip()]
    )
    if countries:
        qs = [signalement for signalement in qs if signalement_matches_country(signalement, countries)]
    return Response(serialize_signalements(qs, request))


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@permission_classes([IsAuthenticated])
def create_signalement(request):
    ensure_demo_signalements()
    payload = normalize_signalement_payload(request)
    serializer = SignalementCreateSerializer(data=payload)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    sig = serializer.save(contributeur=request.user, statut="en_attente")
    for uploaded in request.FILES.getlist("pieces_jointes"):
        PieceJointe.objects.create(
            signalement=sig,
            fichier=uploaded,
            nom_original=uploaded.name,
            taille=uploaded.size,
            media_type=detect_media_type(uploaded.name),
        )
    record_activity(
        "creation",
        f"{request.user.nom_complet} a soumis {sig.reference}",
        actor=request.user,
        signalement=sig,
        statut=sig.statut,
    )
    return Response(SignalementSerializer(sig, context={"request": request}).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detail_signalement(request, pk):
    ensure_demo_signalements()
    try:
        signalement = visible_signalements_for(request.user).get(pk=pk)
    except Signalement.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)
    return Response(SignalementSerializer(signalement, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def valider_signalement(request, pk):
    ensure_demo_signalements()
    if not is_platform_admin(request.user):
        return Response({"error": "Permission insuffisante."}, status=403)
    try:
        sig = Signalement.objects.get(pk=pk)
    except Signalement.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)

    action = request.data.get("action")
    if action == "valider":
        sig.statut = "valide"
        sig.validateur = request.user
        sig.date_validation = timezone.now()
        sig.motif_rejet = ""
        record_activity("validation", f"{sig.reference} a ete valide", actor=request.user, signalement=sig)
    elif action == "rejeter":
        sig.statut = "rejete"
        sig.validateur = request.user
        sig.date_validation = timezone.now()
        sig.motif_rejet = request.data.get("motif", "")
        record_activity("rejet", f"{sig.reference} a ete rejete", actor=request.user, signalement=sig, motif=sig.motif_rejet)
    else:
        return Response({"error": "Action invalide. Utilisez valider ou rejeter."}, status=400)

    sig.save()
    return Response(SignalementSerializer(sig, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_comment(request, pk):
    ensure_demo_signalements()
    try:
        signalement = visible_signalements_for(request.user).get(pk=pk)
    except Signalement.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)

    serializer = SignalCommentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    comment = serializer.save(signalement=signalement, auteur=request.user)
    record_activity("commentaire", f"{request.user.nom_complet} a commente {signalement.reference}", actor=request.user, signalement=signalement)
    return Response({"commentaire": SignalCommentSerializer(comment).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_reaction(request, pk):
    ensure_demo_signalements()
    try:
        signalement = visible_signalements_for(request.user).get(pk=pk)
    except Signalement.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)

    serializer = SignalReactionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    reaction_type = serializer.validated_data["reaction_type"]
    reaction, created = SignalReaction.objects.get_or_create(
        signalement=signalement,
        user=request.user,
        reaction_type=reaction_type,
    )
    if not created:
        reaction.delete()
    else:
        record_activity("reaction", f"{request.user.nom_complet} a marque {signalement.reference} comme {reaction_type}", actor=request.user, signalement=signalement, reaction_type=reaction_type)
    return Response(
        SignalementSerializer(signalement, context={"request": request}).data
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, pk):
    ensure_demo_signalements()
    try:
        signalement = visible_signalements_for(request.user).get(pk=pk)
    except Signalement.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)

    favorite, created = SignalFavorite.objects.get_or_create(signalement=signalement, user=request.user)
    if not created:
        favorite.delete()
    else:
        record_activity("favori", f"{request.user.nom_complet} a enregistre {signalement.reference}", actor=request.user, signalement=signalement)
    return Response(SignalementSerializer(signalement, context={"request": request}).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_narratifs(request):
    ensure_demo_signalements()
    return Response(NarratifSerializer(Narratif.objects.all(), many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    ensure_demo_signalements()
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    sigs = Signalement.objects.filter(date_creation__gte=month_start, statut="valide")
    from actors.models import Acteur

    narratifs_top = Narratif.objects.annotate(nb=Count("signalements")).order_by("-nb")[:5]
    covered_countries = set()
    for signalement in Signalement.objects.filter(statut="valide"):
        covered_countries.update(signalement_countries(signalement))
    for acteur in Acteur.objects.all():
        covered_countries.update(normalize_country_list(acteur.pays_operation))
    return Response(
        {
            "signalements_mois": sigs.count(),
            "elevee": sigs.filter(criticite="elevee").count(),
            "moderee": sigs.filter(criticite="moderee").count(),
            "faible": sigs.filter(criticite="faible").count(),
            "acteurs_documentes": Acteur.objects.count(),
            "pays_couverts": len(covered_countries),
            "membres_actifs": User.objects.filter(is_active=True).count(),
            "narratifs_top": [{"nom": n.nom, "count": n.nb} for n in narratifs_top],
            "derniers_signalements": SignalementSerializer(
                Signalement.objects.filter(statut="valide").order_by("-date_validation")[:4],
                many=True,
                context={"request": request},
            ).data,
            "en_attente": Signalement.objects.filter(statut="en_attente").count(),
            "activites": ActivityItemSerializer(ActivityItem.objects.select_related("actor", "signalement")[:8], many=True).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def workspace(request):
    ensure_demo_signalements()
    mine = Signalement.objects.filter(contributeur=request.user).order_by("-date_creation")
    favoris = Signalement.objects.filter(favoris__user=request.user).distinct().order_by("-date_modification")
    activites = ActivityItem.objects.filter(
        Q(actor=request.user) | Q(signalement__contributeur=request.user) | Q(signalement__statut="valide")
    ).select_related("actor", "signalement")[:12]
    payload = {
        "stats": {
            "mes_signalements": mine.count(),
            "en_attente": mine.filter(statut="en_attente").count(),
            "valides": mine.filter(statut="valide").count(),
            "favoris": favoris.count(),
        },
        "mes_signalements": SignalementSerializer(mine[:8], many=True, context={"request": request}).data,
        "favoris": SignalementSerializer(favoris[:6], many=True, context={"request": request}).data,
        "activites": ActivityItemSerializer(activites, many=True).data,
    }
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_signalements_report(request):
    ensure_demo_signalements()
    try:
        start_date, end_date = parse_report_dates(request)
    except ValueError as error:
        return Response({"error": str(error)}, status=400)

    queryset = filter_signalements_queryset(visible_signalements_for(request.user), request)
    if start_date and end_date:
        if len(str(request.query_params.get("month") or "")) == 7:
            queryset = queryset.filter(date_evenement__gte=start_date, date_evenement__lt=end_date)
        else:
            queryset = queryset.filter(date_evenement__gte=start_date, date_evenement__lte=end_date)
    countries = normalize_country_list(
        [item for item in (request.query_params.get("pays") or "").split(",") if item.strip()]
    )
    if countries:
        queryset = [signalement for signalement in queryset if signalement_matches_country(signalement, countries)]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Reference",
        "Titre",
        "Pays",
        "Date evenement",
        "Type",
        "Criticite",
        "Statut",
        "Acteurs",
        "Narratifs",
        "Contributeur",
        "Description",
    ])

    for signalement in queryset:
        writer.writerow([
            signalement.reference,
            signalement.titre,
            ", ".join(signalement_countries(signalement)),
            signalement.date_evenement.isoformat(),
            signalement.get_type_evenement_display(),
            signalement.get_criticite_display(),
            signalement.get_statut_display(),
            ", ".join(signalement.acteurs_lies.values_list("nom", flat=True)),
            ", ".join(signalement.narratifs.values_list("nom", flat=True)),
            getattr(signalement.contributeur, "nom_complet", ""),
            signalement.description,
        ])

    filename_suffix = (request.query_params.get("month") or "").strip()
    if not filename_suffix and start_date and end_date:
        filename_suffix = f"{start_date.isoformat()}-{end_date.isoformat()}"
    if not filename_suffix:
        filename_suffix = timezone.now().date().isoformat()

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="rapport-signalements-{filename_suffix}.csv"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def activity_feed(request):
    ensure_demo_signalements()
    if is_platform_admin(request.user):
        activities = ActivityItem.objects.select_related("actor", "signalement")[:20]
    else:
        activities = ActivityItem.objects.filter(
            Q(actor=request.user) | Q(signalement__contributeur=request.user) | Q(signalement__statut="valide")
        ).select_related("actor", "signalement")[:20]
    return Response(ActivityItemSerializer(activities, many=True).data)
