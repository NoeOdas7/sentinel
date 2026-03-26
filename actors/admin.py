from django.contrib import admin
from .models import Acteur, Connexion

@admin.register(Acteur)
class ActeurAdmin(admin.ModelAdmin):
    list_display=['nom','type_acteur','score_risque','date_creation']
    list_filter=['type_acteur']
    search_fields=['nom']

@admin.register(Connexion)
class ConnexionAdmin(admin.ModelAdmin):
    list_display=['source','cible','type_lien']
