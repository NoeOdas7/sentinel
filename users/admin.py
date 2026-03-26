from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuthToken, InvitationLink, OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email",
        "nom_complet",
        "role",
        "pays",
        "approval_status",
        "is_active",
        "is_approved",
        "date_joined",
    ]
    list_filter = ["role", "pays", "approval_status", "is_active"]
    search_fields = ["email", "nom_complet"]
    ordering = ["-date_joined"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Infos", {"fields": ("nom_complet", "organisation", "role", "pays")}),
        (
            "Acces",
            {
                "fields": (
                    "approval_status",
                    "approval_decided_at",
                    "first_login_completed",
                    "is_active",
                    "is_approved",
                )
            },
        ),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nom_complet", "role", "pays", "password1", "password2"),
            },
        ),
    )
    actions = ["approuver"]

    def approuver(self, request, queryset):
        queryset.update(
            is_active=True,
            is_approved=True,
            approval_status="approved",
        )

    approuver.short_description = "Approuver les membres selectionnes"


@admin.register(OTPCode)
class OTPAdmin(admin.ModelAdmin):
    list_display = ["user", "code", "created_at", "expires_at", "is_used"]


@admin.register(AuthToken)
class TokenAdmin(admin.ModelAdmin):
    list_display = ["user", "ip_address", "created_at", "is_active"]


@admin.register(InvitationLink)
class InviteAdmin(admin.ModelAdmin):
    list_display = ["email", "role", "created_by", "expires_at", "is_used"]
