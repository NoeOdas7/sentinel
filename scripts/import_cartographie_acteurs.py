import os
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentinel_config.settings")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model

from actors.models import Acteur


NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}
KNOWN_COUNTRIES = [
    "Afghanistan", "Afrique du Sud", "Albanie", "Algerie", "Allemagne", "Andorre", "Angola",
    "Arabie Saoudite", "Argentine", "Armenie", "Australie", "Autriche", "Azerbaidjan", "Bahrein",
    "Bangladesh", "Belgique", "Benin", "Bielorussie", "Birmanie", "Bolivie", "Botswana", "Bresil",
    "Bulgarie", "Burkina Faso", "Burundi", "Cambodge", "Cameroun", "Canada", "Chili", "Chine",
    "Colombie", "Congo", "Coree du Sud", "Coree du Nord", "Costa Rica", "Cote d'Ivoire", "Croatie",
    "Danemark", "Djibouti", "Egypte", "Emirats arabes unis", "Equateur", "Erythree", "Espagne",
    "Estonie", "Eswatini", "Etats-Unis", "Ethiopie", "Finlande", "France", "Gabon", "Gambie", "Ghana",
    "Grece", "Guatemala", "Guinee", "Guinee-Bissau", "Guinee equatoriale", "Haiti", "Honduras",
    "Hongrie", "Inde", "Indonesie", "Irak", "Iran", "Irlande", "Islande", "Israel", "Italie",
    "Japon", "Jordanie", "Kenya", "Koweit", "Laos", "Liban", "Liberia", "Libye", "Madagascar",
    "Malaisie", "Malawi", "Mali", "Maroc", "Mauritanie", "Mexique", "Mozambique", "Namibie",
    "Nepal", "Nicaragua", "Niger", "Nigeria", "Norvege", "Ouganda", "Pakistan", "Palestine", "Panama",
    "Paraguay", "Pays-Bas", "Perou", "Philippines", "Pologne", "Portugal", "Qatar", "RCA",
    "Republique centrafricaine", "Republique democratique du Congo", "Republique dominicaine",
    "Roumanie", "Royaume-Uni", "Russie", "Rwanda", "Senegal", "Serbie", "Sierra Leone", "Singapour",
    "Slovaquie", "Slovenie", "Somalie", "Soudan", "Soudan du Sud", "Sri Lanka", "Suede", "Suisse",
    "Syrie", "Tadjikistan", "Tanzanie", "Tchad", "Thailande", "Togo", "Tunisie", "Turquie",
    "Ukraine", "Uruguay", "Venezuela", "Vietnam", "Yemen", "Zambie", "Zimbabwe",
]


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_lookup(value):
    current = normalize_text(value)
    current = unicodedata.normalize("NFD", current)
    current = "".join(char for char in current if unicodedata.category(char) != "Mn")
    return current.lower()


def read_rows(path):
    with zipfile.ZipFile(path) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", NS):
                shared_strings.append("".join(node.text or "" for node in item.iterfind(".//a:t", NS)))

        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//a:sheetData/a:row", NS):
            values = []
            for cell in row.findall("a:c", NS):
                cell_type = cell.attrib.get("t")
                value = cell.find("a:v", NS)
                if value is None:
                    values.append("")
                elif cell_type == "s":
                    values.append(shared_strings[int(value.text)])
                else:
                    values.append(value.text or "")
            rows.append(values)
        return rows


def infer_actor_type(value):
    current = normalize_lookup(value)
    if "religieux" in current:
        return "rel"
    if "media" in current:
        return "media"
    if "international" in current:
        return "intl"
    if "local" in current or "national" in current:
        return "local"
    return "local"


def infer_countries(value):
    current = normalize_lookup(value)
    found = []
    for country in KNOWN_COUNTRIES:
        if normalize_lookup(country) in current and country not in found:
            found.append("RCA" if country == "Republique centrafricaine" else country)
    if "tchad" in current and "Tchad" not in found:
        found.append("Tchad")
    return found or ["Tchad"]


def main():
    workbook_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "Cartographie_Anti-droits_remplie.xlsx"
    rows = read_rows(workbook_path)
    entries = [row for row in rows[2:] if any(normalize_text(item) for item in row)]
    admin_user = get_user_model().objects.filter(email__iexact=settings.DEMO_ADMIN_EMAIL, is_active=True).first()
    if not admin_user:
        raise SystemExit("Compte admin introuvable.")

    created = 0
    updated = 0
    for row in entries:
        while len(row) < 10:
            row.append("")
        nom, type_raw, pays_raw, zone_short, funding, strategy, messages, description, zone_full, strategy_backup = row[:10]
        nom = normalize_text(nom)
        if not nom or normalize_lookup(nom) == "nom de l'organisation":
            continue
        defaults = {
            "type_acteur": infer_actor_type(type_raw),
            "pays_operation": infer_countries(pays_raw),
            "zone_influence": normalize_text(zone_full or zone_short),
            "sources_financement": normalize_text(funding),
            "strategie_mode_operatoire": normalize_text(strategy or strategy_backup),
            "discours_messages_cles": normalize_text(messages),
            "description": normalize_text(description),
            "contribue_par": admin_user,
        }
        _, was_created = Acteur.objects.update_or_create(nom=nom, defaults=defaults)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1

    print(f"Import termine: {created} cree(s), {updated} mis a jour.")


if __name__ == "__main__":
    main()
