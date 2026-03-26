from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ressource",
            name="espace",
            field=models.CharField(
                choices=[("hub", "Hub de ressources"), ("mou", "MoU US Compact")],
                default="hub",
                max_length=10,
            ),
        ),
    ]
