from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("actors", "0004_acteur_logo_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalacteur",
            name="logo",
            field=models.FileField(blank=True, max_length=100, null=True, upload_to="acteurs/logos/"),
        ),
        migrations.AddField(
            model_name="historicalacteur",
            name="photo",
            field=models.FileField(blank=True, max_length=100, null=True, upload_to="acteurs/photos/"),
        ),
    ]
