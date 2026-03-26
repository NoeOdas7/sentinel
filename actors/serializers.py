from rest_framework import serializers
from .models import Acteur, Connexion

class ConnexionSerializer(serializers.ModelSerializer):
    source_nom=serializers.CharField(source='source.nom',read_only=True)
    cible_nom=serializers.CharField(source='cible.nom',read_only=True)
    type_display=serializers.CharField(source='get_type_lien_display',read_only=True)
    class Meta: model=Connexion; fields='__all__'

class ActeurSerializer(serializers.ModelSerializer):
    type_display=serializers.CharField(source='get_type_acteur_display',read_only=True)
    connexions_sortantes=ConnexionSerializer(many=True,read_only=True)
    class Meta: model=Acteur; fields='__all__'; read_only_fields=['date_creation','date_modification','contribue_par']
