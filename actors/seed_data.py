from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


DATA_FILE = Path(__file__).with_name("radar_doc_dataset.json")

REGIONAL_COUNTRIES = [
    "Bénin",
    "Côte d'Ivoire",
    "Cameroun",
    "Tchad",
    "Sénégal",
    "Burkina Faso",
]

COUNTRY_FIXUPS = {
    "B?nin": "Bénin",
    "C?te d'Ivoire": "Côte d'Ivoire",
    "S?n?gal": "Sénégal",
}

NARRATIVE_RULES = [
    ("Protection de la famille", ("famille", "cellule familiale", "valeurs familiales", "enfant", "vie")),
    ("Religion et morale", ("dieu", "péché", "église", "islam", "relig", "évangile", "mosquée", "imam", "catholique")),
    ("Souverainisme anti-occidental", ("occident", "souverain", "africain", "anti-afric", "impérial", "néocolonial", "maputo")),
    ("Pseudo-science et désinformation", ("pseudo", "stérile", "stérilité", "scientifique", "désinformation", "médicale", "complications")),
    ("Masculinité toxique et contrôle social", ("soumise", "masculinité", "mâle alpha", "polygamie", "virginité", "dépravation")),
    ("Contrôle civique et institutionnel", ("blocage", "parlement", "ministère", "consensus de genève", "terminologies", "espace civique")),
]

TYPE_KEYWORDS = {
    "rel": ("relig", "église", "eglise", "imam", "islam", "catholique", "mosquée", "mosquee", "vodoun", "confessionnel", "prédicateur", "prédication", "confrérie", "dahira", "pasteur"),
    "media": ("média", "media", "radio", "tv", "télé", "tele", "blog", "numérique", "numerique", "influenceur", "blogueur", "chaîne", "chaine", "presse"),
    "intl": ("international", "régional", "regional", "transnational", "union africaine", "onu", "vatican", "administration américaine"),
}

RISK_KEYWORDS = {
    "high": ("parlement", "assemblée", "assemblee", "ministère", "ministere", "gouvernement", "union africaine", "consensus de genève", "maputo", "lobbying", "blocage"),
    "medium": ("réseaux sociaux", "reseaux sociaux", "désinformation", "desinformation", "conférences", "conferences", "financement", "campagnes"),
}


def _clean_text(value):
    current = str(value or "")
    current = current.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    current = current.replace("\xa0", " ")
    current = re.sub(r"\s+", " ", current).strip()
    return current


def _normalize_lookup(value):
    current = unicodedata.normalize("NFD", _clean_text(value))
    current = "".join(char for char in current if unicodedata.category(char) != "Mn")
    return current.lower()


def _load_raw_entries():
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def _infer_actor_type(category, scope):
    lookup = _normalize_lookup(category)
    for actor_type, keywords in TYPE_KEYWORDS.items():
        if any(keyword in lookup for keyword in keywords):
            return actor_type
    return "intl" if scope == "regional" else "local"


def _infer_narratifs(*values):
    joined = " ".join(_clean_text(value) for value in values if value)
    lookup = _normalize_lookup(joined)
    labels = []
    for label, keywords in NARRATIVE_RULES:
        if any(keyword in lookup for keyword in keywords):
            labels.append(label)
    return labels or ["Veille anti-droits"]


def _infer_risk_score(entry, actor_type):
    scope = entry["scope"]
    base = {
        "intl": 78 if scope == "regional" else 70,
        "rel": 68,
        "media": 62,
        "local": 66,
    }.get(actor_type, 60)
    joined = " ".join([
        _clean_text(entry.get("category")),
        _clean_text(entry.get("discours_cles")),
        _clean_text(entry.get("strategies")),
        _clean_text(entry.get("zones_influence")),
    ])
    lookup = _normalize_lookup(joined)
    if any(keyword in lookup for keyword in RISK_KEYWORDS["high"]):
        base += 10
    if any(keyword in lookup for keyword in RISK_KEYWORDS["medium"]):
        base += 5
    if "régime militaire" in lookup or "regime militaire" in lookup:
        base += 4
    return min(base, 95)


def _build_description(entry):
    scope_label = "régional" if entry["scope"] == "regional" else f"pays - {', '.join(entry['countries'])}"
    category = _clean_text(entry["category"])
    return (
        f"Entrée consolidée issue de la cartographie 2025-2026 des mouvements anti-droits "
        f"(tableau {entry['source_table']}, portée {scope_label}, catégorie {category})."
    )


def _build_seed_acteurs():
    seed = []
    for entry in _load_raw_entries():
        category = _clean_text(entry["category"])
        actor_name = _clean_text(entry["actor_name"])
        discourse = _clean_text(entry.get("discours_cles"))
        strategies = _clean_text(entry.get("strategies"))
        zones = _clean_text(entry.get("zones_influence"))
        countries = [COUNTRY_FIXUPS.get(_clean_text(item), _clean_text(item)) for item in entry.get("countries", []) if _clean_text(item)]
        actor_type = _infer_actor_type(category, entry["scope"])
        seed.append(
            {
                "nom": actor_name,
                "type_acteur": actor_type,
                "pays_operation": countries or REGIONAL_COUNTRIES,
                "score_risque": _infer_risk_score(entry, actor_type),
                "sources_financement": "",
                "zone_influence": zones,
                "strategie_mode_operatoire": strategies,
                "discours_messages_cles": discourse,
                "description": _build_description(entry),
                "narratifs_labels": _infer_narratifs(category, discourse, strategies, zones),
            }
        )
    return seed


SEED_ACTEURS = _build_seed_acteurs()


def get_seed_actor_names():
    return [item["nom"] for item in SEED_ACTEURS]


def sync_seed_acteurs(admin_user):
    from actors.models import Acteur
    from signals.models import Narratif

    seed_names = []
    for item in SEED_ACTEURS:
        payload = item.copy()
        labels = payload.pop("narratifs_labels", [])
        payload["contribue_par"] = admin_user
        acteur, _ = Acteur.objects.update_or_create(nom=payload["nom"], defaults=payload)
        if labels:
            narratifs = [Narratif.objects.get_or_create(nom=label)[0] for label in labels]
            acteur.narratifs.set(narratifs)
        else:
            acteur.narratifs.clear()
        seed_names.append(acteur.nom)

    Acteur.objects.filter(contribue_par=admin_user).exclude(nom__in=seed_names).delete()
