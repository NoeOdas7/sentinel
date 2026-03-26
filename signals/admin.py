from django.contrib import admin
from .models import Signalement, Narratif, PieceJointe

@admin.register(Narratif)
class NarratifAdmin(admin.ModelAdmin):
    list_display=['nom']

@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    list_display=['reference','titre','pays','criticite','statut','date_creation']
    list_filter=['statut','criticite','pays','type_evenement']
    search_fields=['reference','titre']
    readonly_fields=['reference','date_creation','date_modification']
