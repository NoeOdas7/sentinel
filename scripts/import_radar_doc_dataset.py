import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentinel_config.settings")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model

from actors.seed_data import SEED_ACTEURS, sync_seed_acteurs


def main():
    user_model = get_user_model()
    admin_user = user_model.objects.filter(
        email__iexact=settings.DEMO_ADMIN_EMAIL,
        is_active=True,
    ).first()
    if not admin_user:
        raise SystemExit("Compte admin RADAR introuvable.")

    sync_seed_acteurs(admin_user)
    print(f"Import RADAR termine: {len(SEED_ACTEURS)} acteur(s) synchronise(s).")


if __name__ == "__main__":
    main()
