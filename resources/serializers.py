from rest_framework import serializers

from .models import Ressource


class RessourceSerializer(serializers.ModelSerializer):
    est_nouvelle = serializers.ReadOnlyField()
    categorie_display = serializers.CharField(source="get_categorie_display", read_only=True)
    espace_display = serializers.CharField(source="get_espace_display", read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        file_type = attrs.get("type_fichier", getattr(self.instance, "type_fichier", None))
        fichier = attrs.get("fichier", getattr(self.instance, "fichier", None))
        lien_externe = attrs.get("lien_externe", getattr(self.instance, "lien_externe", ""))

        if file_type == "lien":
            if not lien_externe:
                raise serializers.ValidationError({"lien_externe": "Un lien externe est requis pour ce type de ressource."})
        elif not fichier and not lien_externe:
            raise serializers.ValidationError({"fichier": "Un fichier ou un lien externe est requis pour ce type de ressource."})

        return attrs

    class Meta:
        model = Ressource
        fields = "__all__"
        read_only_fields = ["nb_telechargements", "date_creation", "contributeur", "statut"]
