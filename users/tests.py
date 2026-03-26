from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import OTPCode, User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_DEMO_FALLBACK=True,
    DEMO_ADMIN_EMAIL="admin@odas.org",
    DEMO_ADMIN_PASSWORD="admin123",
    DEMO_ADMIN_NAME="Admin Demo ODAS",
)
class AuthenticationFlowsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_demo_admin_can_login_directly(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "admin@odas.org", "password": "admin123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["role"], "admin")

    def test_admin_approval_sends_first_login_code(self):
        admin = User.objects.create_user(
            email="owner@odas.org",
            password="secret123",
            nom_complet="Owner Admin",
            role="admin",
            is_active=True,
            is_approved=True,
            is_staff=True,
            approval_status="approved",
            first_login_completed=True,
        )
        pending_user = User.objects.create_user(
            email="user@example.com",
            password="secret123",
            nom_complet="User Pending",
            role="contributeur",
            is_active=False,
            is_approved=False,
            approval_status="pending",
        )
        self.client.force_authenticate(user=admin)

        response = self.client.patch(
            f"/api/v1/auth/members/{pending_user.id}/",
            {"decision": "approve"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        pending_user.refresh_from_db()
        self.assertTrue(pending_user.is_active)
        self.assertTrue(pending_user.is_approved)
        self.assertEqual(pending_user.approval_status, "approved")
        self.assertFalse(pending_user.first_login_completed)
        self.assertTrue(OTPCode.objects.filter(user=pending_user, is_used=False).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("approuve", mail.outbox[0].subject.lower())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", EMAIL_DEMO_FALLBACK=True)
    def test_console_email_backend_returns_demo_code(self):
        user = User.objects.create_user(
            email="demo.user@example.com",
            password="secret123",
            nom_complet="Demo User",
            role="contributeur",
            is_active=True,
            is_approved=True,
            approval_status="approved",
            first_login_completed=True,
        )

        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "secret123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("demo_code", response.data)
