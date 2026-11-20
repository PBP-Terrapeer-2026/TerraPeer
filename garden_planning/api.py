"""Garden Planning: awalnya CRUD Plan; PlanPlant/Pot untuk fase setelah checkpoint."""
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Plan


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id", "name", "status", "location_name", "latitude", "longitude",
            "environment_profile", "is_draft", "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Plan.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
