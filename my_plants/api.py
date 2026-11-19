"""My Plants. Transisi growth_stage tetap lewat alur foto di fase final."""
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Plant


class MyPlantSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    days_growing = serializers.IntegerField(read_only=True)

    class Meta:
        model = Plant
        fields = (
            "id", "name", "species_name", "planted_on", "growth_stage", "status",
            "days_growing", "notes", "perenual_species_id", "created_at", "updated_at",
        )
        # Jangan bypass syarat foto saat pindah tahap pertumbuhan dari sistem web.
        read_only_fields = ("id", "growth_stage", "status", "days_growing", "created_at", "updated_at")

    def validate_planted_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Planting date cannot be in the future.")
        return value


class MyPlantViewSet(viewsets.ModelViewSet):
    serializer_class = MyPlantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Plant.objects.for_user(self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
