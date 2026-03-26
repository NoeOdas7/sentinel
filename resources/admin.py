from django.contrib import admin
from .models import Ressource

@admin.register(Ressource)
class RessourceAdmin(admin.ModelAdmin):
    list_display=['titre','categorie','statut','contributeur','date_creation']
    list_filter=['statut','categorie','langue']
    search_fields=['titre']
    actions=['publier']
    def publier(self,req,qs): qs.update(statut='publie')
    publier.short_description='Publier les ressources sélectionnées'
