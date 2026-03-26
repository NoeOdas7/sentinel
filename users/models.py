from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

import random
import secrets
import string


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("is_approved", True)
        extra.setdefault("approval_status", "approved")
        extra.setdefault("first_login_completed", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLES = [
        ("admin", "Administrateur"),
        ("analyste", "Analyste ODAS"),
        ("moderateur", "Moderateur pays"),
        ("contributeur", "Contributeur"),
        ("bailleur", "Bailleur"),
    ]
    PAYS = [
        ("benin", "Benin"),
        ("cameroun", "Cameroun"),
        ("cote_ivoire", "Cote d'Ivoire"),
        ("guinee", "Guinee"),
        ("madagascar", "Madagascar"),
        ("mali", "Mali"),
        ("rca", "RCA"),
        ("regional", "Regional"),
    ]
    APPROVAL_STATUS = [
        ("pending", "En attente"),
        ("approved", "Approuve"),
        ("rejected", "Refuse"),
    ]

    email = models.EmailField(unique=True)
    nom_complet = models.CharField(max_length=200)
    organisation = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=20, choices=ROLES, default="contributeur")
    pays = models.CharField(max_length=20, choices=PAYS, blank=True)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default="pending")
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    first_login_completed = models.BooleanField(default=False)
    approval_decided_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom_complet"]

    class Meta:
        verbose_name = "Membre"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.nom_complet} <{self.email}>"

    @property
    def initiales(self):
        parts = self.nom_complet.split()
        return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else self.nom_complet[:2].upper()


class OTPCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate():
        return "".join(random.choices(string.digits, k=6))

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def use(self):
        self.is_used = True
        self.save(update_fields=["is_used"])


class AuthToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_tokens")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    @property
    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at

    def revoke(self):
        self.is_active = False
        self.save(update_fields=["is_active"])


class InvitationLink(models.Model):
    email = models.EmailField()
    role = models.CharField(max_length=20, default="contributeur")
    pays = models.CharField(max_length=20, blank=True)
    token = models.CharField(max_length=64, unique=True, default=secrets.token_hex)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
