import json

from django.db import migrations, models


def prepare_signalement_countries(apps, schema_editor):
    Signalement = apps.get_model("signals", "Signalement")
    code_labels = {
        "benin": "Benin",
        "cameroun": "Cameroun",
        "cote_ivoire": "Cote d'Ivoire",
        "guinee": "Guinee",
        "madagascar": "Madagascar",
        "mali": "Mali",
        "rca": "RCA",
    }
    for signalement in Signalement.objects.all():
        value = signalement.pays
        if value:
            countries = [code_labels.get(str(value).lower(), str(value))]
        else:
            countries = []
        signalement.pays = json.dumps(countries, ensure_ascii=False)
        signalement.save(update_fields=["pays"])


class Migration(migrations.Migration):

    dependencies = [
        ("signals", "0003_piecejointe_media_type_and_more"),
    ]

    operations = [
        migrations.RunPython(prepare_signalement_countries, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="signalement",
            name="pays",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
