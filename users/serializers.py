from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    initiales = serializers.ReadOnlyField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    pays_display = serializers.CharField(source="get_pays_display", read_only=True)
    approval_status_display = serializers.CharField(source="get_approval_status_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "nom_complet",
            "organisation",
            "role",
            "role_display",
            "pays",
            "pays_display",
            "approval_status",
            "approval_status_display",
            "initiales",
            "is_active",
            "is_approved",
            "first_login_completed",
            "date_joined",
            "last_login_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_active",
            "is_approved",
            "approval_status",
            "date_joined",
            "first_login_completed",
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["nom_complet", "organisation", "pays"]
