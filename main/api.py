"""Garden Journal: gunakan kepemilikan Plant dan simpan snapshot nama tanaman."""
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from my_plants.models import Plant
from .models import GardenJournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    plant = serializers.PrimaryKeyRelatedField(queryset=Plant.objects.none())

    class Meta:
        model = GardenJournalEntry
        fields = (
            "id", "plant", "plant_name", "entry_date", "entry_type", "title",
            "notes", "harvest_quantity", "harvest_unit", "weather_summary",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "plant_name", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["plant"].queryset = Plant.objects.for_user(request.user)

    def validate(self, attrs):
        entry_type = attrs.get("entry_type", getattr(self.instance, "entry_type", "growth"))
        quantity = attrs.get("harvest_quantity", getattr(self.instance, "harvest_quantity", None))
        if entry_type == "harvest":
            if quantity is None or quantity < 0:
                raise serializers.ValidationError({"harvest_quantity": "A nonnegative quantity is required for harvest."})
        else:
            attrs["harvest_quantity"] = None
            attrs["harvest_unit"] = ""
        return attrs


class JournalEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GardenJournalEntry.objects.filter(user=self.request.user).select_related("plant")

    def perform_create(self, serializer):
        plant = serializer.validated_data["plant"]
        serializer.save(user=self.request.user, plant_name=plant.name)

    def perform_update(self, serializer):
        plant = serializer.validated_data.get("plant", serializer.instance.plant)
        if plant is None:
            raise serializers.ValidationError({"plant": "Select a plant owned by this account."})
        serializer.save(plant_name=plant.name)
