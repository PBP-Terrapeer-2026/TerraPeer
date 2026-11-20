"""Garden Setup: data ruang tanam milik masing-masing pengguna."""
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import GrowingSpace


class GrowingSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrowingSpace
        fields = (
            "id", "name", "environment", "space_type", "other_space_type",
            "geocoding_id", "city", "region", "country", "latitude",
            "longitude", "timezone", "sunlight_range", "light_exposure",
            "growing_medium", "rain_access", "support_available",
            "pot_capacity", "care_availability", "notes", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        environment = attrs.get("environment", getattr(instance, "environment", None))
        rain_access = attrs.get("rain_access", getattr(instance, "rain_access", None))
        space_type = attrs.get("space_type", getattr(instance, "space_type", None))
        other_type = attrs.get("other_space_type", getattr(instance, "other_space_type", ""))
        if environment == GrowingSpace.Environment.INDOOR and rain_access == GrowingSpace.RainAccess.EXPOSED:
            raise serializers.ValidationError({"rain_access": "Indoor spaces must be sheltered."})
        if space_type == GrowingSpace.SpaceType.OTHER and not (other_type or "").strip():
            raise serializers.ValidationError({"other_space_type": "Specify the space type."})
        if space_type != GrowingSpace.SpaceType.OTHER:
            attrs["other_space_type"] = ""
        return attrs


class GrowingSpaceViewSet(viewsets.ModelViewSet):
    serializer_class = GrowingSpaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GrowingSpace.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
