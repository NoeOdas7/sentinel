from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import ActivityItem, SignalComment, SignalReaction, Signalement
from .views import ensure_demo_signalements
from users.models import User


class SignalementFlowsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="secret123",
            nom_complet="Admin User",
            role="admin",
            is_active=True,
            is_approved=True,
            is_staff=True,
            approval_status="approved",
            first_login_completed=True,
        )
        self.member = User.objects.create_user(
            email="member@example.com",
            password="secret123",
            nom_complet="Member User",
            role="contributeur",
            is_active=True,
            is_approved=True,
            approval_status="approved",
            first_login_completed=True,
        )

    def test_demo_signalements_seeded(self):
        ensure_demo_signalements()
        self.assertGreaterEqual(Signalement.objects.count(), 5)
        self.assertTrue(ActivityItem.objects.exists())

    def test_validation_moves_signalement_to_valid(self):
        ensure_demo_signalements()
        pending = Signalement.objects.filter(statut="en_attente").first()
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            f"/api/v1/signals/{pending.id}/valider/",
            {"action": "valider"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.statut, "valide")
        self.assertEqual(pending.validateur, self.admin)

    def test_create_signalement_is_pending_until_validation(self):
        self.client.force_authenticate(user=self.member)

        create_response = self.client.post(
            "/api/v1/signals/create/",
            {
                "titre": "Campagne numerique de desinformation",
                "pays": "benin",
                "date_evenement": "2026-03-24",
                "type_evenement": "numerique",
                "criticite": "moderee",
                "description": "Une campagne coordonnee diffuse de fausses informations sur les droits sexuels et reproductifs dans plusieurs groupes sociaux.",
                "narratifs": [],
                "acteurs_lies": [],
                "fiabilite": "probable",
                "confidentialite": "membres",
                "sources_url": ["https://example.org/source"],
                "pieces_jointes": [
                    SimpleUploadedFile("capture.jpg", b"fake-image-content", content_type="image/jpeg")
                ],
            },
            format="multipart",
        )

        self.assertEqual(create_response.status_code, 201)
        signalement_id = create_response.data["id"]
        created = Signalement.objects.get(id=signalement_id)
        self.assertEqual(created.statut, "en_attente")
        self.assertEqual(created.contributeur, self.member)
        self.assertEqual(created.pieces_jointes.count(), 1)

        self.client.force_authenticate(user=self.admin)
        validate_response = self.client.post(
            f"/api/v1/signals/{signalement_id}/valider/",
            {"action": "valider"},
            format="json",
        )

        self.assertEqual(validate_response.status_code, 200)
        created.refresh_from_db()
        self.assertEqual(created.statut, "valide")

    def test_comment_reaction_and_workspace_flow(self):
        ensure_demo_signalements()
        signalement = Signalement.objects.filter(statut="valide").first()
        self.client.force_authenticate(user=self.member)

        comment_response = self.client.post(
            f"/api/v1/signals/{signalement.id}/commentaires/",
            {"contenu": "Verification en cours avec pieces complementaires.", "mentions": ["admin@odas.org"]},
            format="json",
        )
        reaction_response = self.client.post(
            f"/api/v1/signals/{signalement.id}/reactions/",
            {"reaction_type": "utile"},
            format="json",
        )
        favorite_response = self.client.post(f"/api/v1/signals/{signalement.id}/favori/")
        workspace_response = self.client.get("/api/v1/signals/workspace/")

        self.assertEqual(comment_response.status_code, 200)
        self.assertEqual(reaction_response.status_code, 200)
        self.assertEqual(favorite_response.status_code, 200)
        self.assertEqual(workspace_response.status_code, 200)
        self.assertEqual(SignalComment.objects.filter(signalement=signalement, auteur=self.member).count(), 1)
        self.assertEqual(SignalReaction.objects.filter(signalement=signalement, user=self.member, reaction_type="utile").count(), 1)
        self.assertGreaterEqual(workspace_response.data["stats"]["favoris"], 1)
