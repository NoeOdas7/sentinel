from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("actors", "0003_acteur_discours_messages_cles_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="acteur",
            name="logo",
            field=models.FileField(blank=True, null=True, upload_to="acteurs/logos/"),
        ),
        migrations.AddField(
            model_name="acteur",
            name="photo",
            field=models.FileField(blank=True, null=True, upload_to="acteurs/photos/"),
        ),
    ]
