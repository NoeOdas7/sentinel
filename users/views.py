import datetime
import secrets

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AuthToken, InvitationLink, OTPCode
from .serializers import UserProfileSerializer, UserSerializer

User = get_user_model()


def is_platform_admin(user):
    return bool(
        user
        and user.is_authenticated
        and str(user.email).strip().lower() == settings.DEMO_ADMIN_EMAIL.strip().lower()
    )


def get_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR")


def issue_auth_token(user, request):
    token_val = secrets.token_hex(32)
    AuthToken.objects.create(
        user=user,
        token=token_val,
        expires_at=timezone.now() + datetime.timedelta(days=7),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        ip_address=get_ip(request),
    )
    user.last_login_at = timezone.now()
    if not user.first_login_completed:
        user.first_login_completed = True
        user.save(update_fields=["last_login_at", "first_login_completed"])
    else:
        user.save(update_fields=["last_login_at"])
    return token_val


def should_expose_demo_code():
    backend = getattr(settings, "EMAIL_BACKEND", "")
    if not getattr(settings, "EMAIL_DEMO_FALLBACK", False):
        return False
    return (
        "console.EmailBackend" in backend
        or (
            settings.DEBUG
            and (not getattr(settings, "EMAIL_HOST_USER", "") or not getattr(settings, "EMAIL_HOST_PASSWORD", ""))
        )
    )


def with_demo_code(payload, code):
    data = dict(payload)
    if code and should_expose_demo_code():
        data["demo_code"] = code
    return data


def generate_otp(user, lifetime_seconds):
    OTPCode.objects.filter(user=user, is_used=False).update(is_used=True)
    code = OTPCode.generate()
    otp = OTPCode.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now() + datetime.timedelta(seconds=lifetime_seconds),
    )
    return otp


def send_otp_email(user, code, intro_text, subject):
    html = (
        '<div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#0d1117">'
        '<div style="background:linear-gradient(145deg,#08111d,#12263a);border:1px solid #00d4aa33;border-radius:24px;padding:36px">'
        '<div style="display:inline-block;padding:6px 12px;border-radius:999px;background:#00d4aa18;color:#00d4aa;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:18px">SENTINEL</div>'
        '<div style="color:#eef7ff;font-size:24px;font-weight:800;line-height:1.3;margin-bottom:12px">Bonjour '
        + user.nom_complet
        + "</div>"
        '<div style="color:#9db3c5;font-size:14px;line-height:1.7;margin-bottom:24px">'
        + intro_text
        + "</div>"
        '<div style="background:#050d18;border:1px solid #00d4aa44;border-radius:18px;padding:22px 20px;text-align:center;margin-bottom:22px">'
        '<div style="color:#5ed7c1;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px">Code</div>'
        '<div style="color:#ffffff;font-size:42px;font-weight:900;letter-spacing:14px;font-family:monospace">'
        + code
        + "</div></div>"
        '<div style="color:#89a1b4;font-size:12px;line-height:1.8">Ce code est a usage unique. Ne le partagez pas.</div>'
        "</div></div>"
    )

    send_mail(
        subject=subject,
        message=(
            f"Bonjour {user.nom_complet},\n\n"
            f"{intro_text}\n\n"
            f"Code : {code}\n\n"
            "- SENTINEL / Centre ODAS"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=False,
    )


def send_access_approved_email(user, code):
    send_otp_email(
        user,
        code,
        "Votre demande d'acces a ete approuvee. Utilisez ce code pour votre premiere connexion apres avoir saisi votre email et votre mot de passe.",
        "[SENTINEL] Votre acces est approuve",
    )


def send_access_rejected_email(user):
    send_mail(
        subject="[SENTINEL] Votre demande n'a pas ete approuvee",
        message=(
            f"Bonjour {user.nom_complet},\n\n"
            "Votre demande d'acces a SENTINEL n'a pas ete approuvee pour le moment.\n"
            "Vous pouvez contacter l'equipe ODAS si vous pensez qu'il s'agit d'une erreur.\n\n"
            "- SENTINEL / Centre ODAS"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def ensure_demo_admin_user():
    email = settings.DEMO_ADMIN_EMAIL.strip().lower()
    password = settings.DEMO_ADMIN_PASSWORD
    if not email or not password:
        return
    defaults = {
        "nom_complet": settings.DEMO_ADMIN_NAME,
        "role": "admin",
        "organisation": "Centre ODAS",
        "pays": "regional",
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
        "is_approved": True,
        "approval_status": "approved",
        "first_login_completed": True,
    }
    user, created = User.objects.get_or_create(email=email, defaults=defaults)
    changed = created
    for field, value in defaults.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed = True
    if not user.check_password(password):
        user.set_password(password)
        changed = True
    if changed:
        user.save()


@api_view(["POST"])
@permission_classes([AllowAny])
def login_step1(request):
    ensure_demo_admin_user()

    email = request.data.get("email", "").lower().strip()
    password = request.data.get("password", "")
    if not email or not password:
        return Response({"error": "Email et mot de passe requis."}, status=400)

    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "Identifiants incorrects."}, status=401)
    if user.approval_status == "rejected":
        return Response({"error": "Cette demande a ete refusee par l'administrateur."}, status=403)
    if not user.is_active:
        return Response({"error": "Compte en attente d'approbation."}, status=403)

    user = authenticate(request, email=email, password=password)
    if user is None:
        return Response({"error": "Identifiants incorrects."}, status=401)

    if is_platform_admin(user):
        token_val = issue_auth_token(user, request)
        return Response({"token": token_val, "user": UserSerializer(user).data})

    first_login_code = (
        OTPCode.objects.filter(user=user, is_used=False, expires_at__gt=timezone.now()).order_by("-created_at").first()
        if not user.first_login_completed
        else None
    )
    if first_login_code:
        return Response(
            with_demo_code(
                {
                    "message": "Votre acces a ete valide. Utilisez le code recu par email pour cette premiere connexion.",
                    "email": email,
                    "first_login": True,
                },
                first_login_code.code,
            )
        )

    otp = generate_otp(user, settings.OTP_EXPIRY_SECONDS)
    send_otp_email(
        user,
        otp.code,
        "Voici votre code de verification pour vous connecter a votre espace SENTINEL.",
        "[SENTINEL] Code de verification",
    )
    return Response(with_demo_code({"message": "Code envoye a " + email, "email": email}, otp.code))


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp(request):
    email = request.data.get("email", "").lower().strip()
    code = request.data.get("code", "").strip()
    if not email or not code:
        return Response({"error": "Email et code requis."}, status=400)

    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        return Response({"error": "Utilisateur introuvable."}, status=404)

    otp = OTPCode.objects.filter(user=user, code=code, is_used=False).order_by("-created_at").first()
    if not otp or not otp.is_valid:
        return Response({"error": "Code incorrect ou expire."}, status=401)

    otp.use()
    token_val = issue_auth_token(user, request)
    return Response({"token": token_val, "user": UserSerializer(user).data})


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_otp(request):
    email = request.data.get("email", "").lower().strip()
    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        return Response({"message": "Si cet email existe, un code a ete envoye."})

    recent = OTPCode.objects.filter(
        user=user,
        created_at__gte=timezone.now() - datetime.timedelta(seconds=60),
    ).exists()
    if recent:
        return Response({"error": "Attendez avant de redemander un code."}, status=429)

    lifetime = settings.FIRST_LOGIN_CODE_EXPIRY_HOURS * 3600 if not user.first_login_completed else settings.OTP_EXPIRY_SECONDS
    otp = generate_otp(user, lifetime)
    intro = (
        "Votre acces est pret. Voici un nouveau code pour terminer votre premiere connexion."
        if not user.first_login_completed
        else "Voici votre nouveau code de verification pour vous connecter."
    )
    send_otp_email(user, otp.code, intro, "[SENTINEL] Nouveau code de connexion")
    return Response(with_demo_code({"message": "Nouveau code envoye."}, otp.code))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    if request.auth:
        AuthToken.objects.filter(token=request.auth).update(is_active=False)
    return Response({"message": "Deconnecte."})


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    email = request.data.get("email", "").lower().strip()
    password = request.data.get("password", "")
    nom = request.data.get("nom_complet", "").strip()
    organisation = request.data.get("organisation", "").strip()
    pays = request.data.get("pays", "")
    invite_token = request.data.get("invitation_token", "")
    requested_role = request.data.get("role", "contributeur")

    valid_roles = {choice[0] for choice in User.ROLES}
    allowed_requested_roles = valid_roles - {"admin"}

    if not all([email, password, nom]):
        return Response({"error": "Nom, email et mot de passe requis."}, status=400)
    if requested_role not in allowed_requested_roles:
        requested_role = "contributeur"
    if User.objects.filter(email=email).exists():
        return Response({"error": "Un compte existe deja avec cet email."}, status=400)

    is_approved = False
    role = requested_role
    approval_status = "pending"
    first_login_completed = False

    if invite_token:
        try:
            invitation = InvitationLink.objects.get(token=invite_token, email=email)
        except InvitationLink.DoesNotExist:
            return Response({"error": "Lien d'invitation invalide."}, status=400)

        if not invitation.is_valid:
            return Response({"error": "Lien d'invitation expire ou deja utilise."}, status=400)

        is_approved = True
        approval_status = "approved"
        first_login_completed = True
        role = invitation.role
        pays = invitation.pays or pays
        invitation.is_used = True
        invitation.save(update_fields=["is_used"])

    User.objects.create_user(
        email=email,
        password=password,
        nom_complet=nom,
        organisation=organisation,
        pays=pays,
        role=role,
        is_active=is_approved,
        is_approved=is_approved,
        approval_status=approval_status,
        first_login_completed=first_login_completed,
    )

    if is_approved:
        return Response({"message": "Compte cree. Connectez-vous."}, status=201)

    admin_emails = list(User.objects.filter(role="admin", is_active=True).values_list("email", flat=True))
    if admin_emails:
        send_mail(
            subject="[SENTINEL] Nouvelle demande d'acces - " + nom,
            message=(
                "Une nouvelle demande d'acces a ete soumise.\n\n"
                f"Nom : {nom}\n"
                f"Email : {email}\n"
                f"Organisation : {organisation or '-'}\n"
                f"Pays : {pays or '-'}\n"
                f"Role souhaite : {role}\n\n"
                "Connectez-vous pour valider ou refuser cette demande."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True,
        )
    return Response(
        {
            "message": "Demande envoyee. Un administrateur doit maintenant valider votre acces.",
            "pending": True,
        },
        status=201,
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method == "GET":
        return Response(UserSerializer(request.user).data)

    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sessions(request):
    tokens = AuthToken.objects.filter(
        user=request.user,
        is_active=True,
        expires_at__gt=timezone.now(),
    ).order_by("-last_used")
    return Response(
        [
            {
                "id": token.id,
                "ip": token.ip_address,
                "agent": token.user_agent[:60],
                "created": token.created_at,
                "is_current": token.token == request.auth,
            }
            for token in tokens
        ]
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def revoke_session(request, sid):
    try:
        token = AuthToken.objects.get(id=sid, user=request.user)
    except AuthToken.DoesNotExist:
        return Response({"error": "Introuvable."}, status=404)

    token.revoke()
    return Response({"message": "Session revoquee."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite(request):
    if not is_platform_admin(request.user):
        return Response({"error": "Permission insuffisante."}, status=403)

    email = request.data.get("email", "").lower().strip()
    role = request.data.get("role", "contributeur")
    pays = request.data.get("pays", "")
    valid_roles = {choice[0] for choice in User.ROLES}
    valid_pays = {choice[0] for choice in User.PAYS}

    if not email:
        return Response({"error": "Email requis."}, status=400)
    if role not in valid_roles:
        return Response({"error": "Role invalide."}, status=400)
    if pays and pays not in valid_pays:
        return Response({"error": "Pays invalide."}, status=400)

    token = secrets.token_hex(32)
    expiry = timezone.now() + datetime.timedelta(hours=48)
    InvitationLink.objects.create(
        email=email,
        role=role,
        pays=pays,
        token=token,
        created_by=request.user,
        expires_at=expiry,
    )

    invite_url = settings.FRONTEND_URL + "/auth?invite=" + token + "&email=" + email
    send_mail(
        subject="[SENTINEL] Invitation a rejoindre la plateforme",
        message="Vous avez ete invite(e).\nLien (valide 48h) : " + invite_url,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    return Response({"message": "Invitation envoyee a " + email, "url": invite_url}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    old_pw = request.data.get("old_password", "")
    new_pw = request.data.get("new_password", "")
    if not old_pw or not new_pw:
        return Response({"error": "Ancien et nouveau mot de passe requis."}, status=400)
    if not request.user.check_password(old_pw):
        return Response({"error": "Mot de passe actuel incorrect."}, status=400)
    if len(new_pw) < 8:
        return Response({"error": "Le mot de passe doit faire au moins 8 caracteres."}, status=400)
    request.user.set_password(new_pw)
    request.user.save(update_fields=["password"])
    AuthToken.objects.filter(user=request.user).exclude(token=request.auth).update(is_active=False)
    return Response({"message": "Mot de passe modifie."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def members_list(request):
    if not is_platform_admin(request.user):
        return Response({"error": "Permission insuffisante."}, status=403)

    users = User.objects.all()
    role = request.query_params.get("role")
    pays = request.query_params.get("pays")
    pending = request.query_params.get("pending")
    approval_status = request.query_params.get("approval_status")

    if role:
        users = users.filter(role=role)
    if pays:
        users = users.filter(pays=pays)
    if pending == "true":
        users = users.filter(approval_status="pending")
    elif pending == "false":
        users = users.exclude(approval_status="pending")
    if approval_status:
        users = users.filter(approval_status=approval_status)

    return Response(UserSerializer(users, many=True).data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_member(request, uid):
    if not is_platform_admin(request.user):
        return Response({"error": "Acces refuse."}, status=403)

    try:
        user = User.objects.get(id=uid)
    except User.DoesNotExist:
        return Response({"error": "Utilisateur introuvable."}, status=404)

    valid_roles = {choice[0] for choice in User.ROLES}
    decision = request.data.get("decision")
    role = request.data.get("role")

    if role:
        if role not in valid_roles:
            return Response({"error": "Role invalide."}, status=400)
        user.role = role

    if decision == "approve":
        user.is_active = True
        user.is_approved = True
        user.approval_status = "approved"
        user.first_login_completed = False
        user.approval_decided_at = timezone.now()
        otp = generate_otp(user, settings.FIRST_LOGIN_CODE_EXPIRY_HOURS * 3600)
        user.save()
        send_access_approved_email(user, otp.code)
    elif decision == "reject":
        user.is_active = False
        user.is_approved = False
        user.approval_status = "rejected"
        user.approval_decided_at = timezone.now()
        OTPCode.objects.filter(user=user, is_used=False).update(is_used=True)
        user.save()
        send_access_rejected_email(user)
    else:
        if request.data.get("is_active") is not None:
            is_active = bool(request.data["is_active"])
            user.is_active = is_active
            if is_active:
                user.is_approved = True
                user.approval_status = "approved"
            elif user.is_approved or user.approval_status == "approved":
                user.is_approved = True
                user.approval_status = "approved"
            else:
                user.is_approved = False
                user.approval_status = "rejected"
            user.approval_decided_at = timezone.now()
        user.save()

    response_data = UserSerializer(user).data
    if decision == "approve":
        response_data = with_demo_code(response_data, otp.code)
    return Response(response_data)
