from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Acteur, Connexion
from .seed_data import SEED_ACTEURS, sync_seed_acteurs


User = get_user_model()


class ActeurApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='demo1234',
            nom_complet='Admin Demo',
            role='admin',
            is_active=True,
            is_approved=True,
            approval_status='approved',
            first_login_completed=True,
        )
        self.client.force_authenticate(self.user)
        self.actor_ci = Acteur.objects.create(
            nom="Alliance Civique",
            type_acteur='local',
            pays_operation=["Côte d'Ivoire", 'Bénin'],
            score_risque=54,
            zone_influence='Universités, parlement',
            strategie_mode_operatoire='Lobbying et campagnes',
            discours_messages_cles='Protection de la famille',
        )
        self.actor_cm = Acteur.objects.create(
            nom='Family Watch Demo',
            type_acteur='intl',
            pays_operation=['Cameroun'],
            score_risque=84,
        )
        Connexion.objects.create(source=self.actor_cm, cible=self.actor_ci, type_lien='partenaire')

    def test_list_acteurs_can_filter_by_country(self):
        response = self.client.get('/api/v1/actors/', {'pays': "Côte d'Ivoire"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['nom'], 'Alliance Civique')

    def test_network_data_can_filter_by_country(self):
        response = self.client.get('/api/v1/actors/network/', {'pays': 'Cameroun'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload['nodes']), 1)
        self.assertEqual(payload['nodes'][0]['nom'], 'Family Watch Demo')
        self.assertEqual(payload['edges'], [])

    def test_download_acteur_profile_returns_attachment(self):
        response = self.client.get(f'/api/v1/actors/{self.actor_ci.id}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn('Alliance Civique', response.content.decode('utf-8'))


class RadarSeedDataTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email='admin@odas.org',
            password='admin123',
            nom_complet='Admin Demo ODAS',
            role='admin',
            is_active=True,
            is_approved=True,
            approval_status='approved',
            first_login_completed=True,
        )

    def test_radar_seed_dataset_contains_regional_and_country_entries(self):
        self.assertGreaterEqual(len(SEED_ACTEURS), 60)
        names = {item['nom'] for item in SEED_ACTEURS}
        self.assertIn("Conférence Épiscopale du Bénin / Archidiocèse de Cotonou", names)
        self.assertIn("Collectif And Samm Jikko Yi Branche féminine Ndeyi Askan Yi (Sokhna Ndeye Diop, épouse du député Alioune Badara Ndao du PASTEF)", names)
        self.assertTrue(any("Human Life International (HLI)" in name for name in names))

    def test_sync_seed_acteurs_creates_document_based_entries(self):
        sync_seed_acteurs(self.admin_user)
        self.assertTrue(Acteur.objects.filter(nom__icontains="Doc-Jeff de Sarh").exists())
        self.assertTrue(Acteur.objects.filter(nom__icontains="Conseil Supérieur Islamique").exists())
