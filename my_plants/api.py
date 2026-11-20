"""My Plants REST API for the Flutter app (/api/v1/my-plants/).

Transisi growth_stage tetap lewat alur foto di situs web, jadi growth_stage
dan status read-only di API.
"""
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
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

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Plant name cannot be blank.")
        return value

    def validate_species_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Species name cannot be blank.")
        return value

    def validate_planted_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Planting date cannot be in the future.")
        return value


ORDERING_FIELDS = {
    "name": ("name", "-pk"),
    "-name": ("-name", "-pk"),
    "planted_on": ("planted_on", "pk"),
    "-planted_on": ("-planted_on", "-pk"),
    "-created_at": ("-created_at", "-pk"),
}

LIST_PARAMETERS = [
    OpenApiParameter(
        "search", OpenApiTypes.STR,
        description="Case-insensitive match on plant name or species name.",
    ),
    OpenApiParameter(
        "status", OpenApiTypes.STR, enum=["active", "finished"],
        description="`active` = every stage except Finished.",
    ),
    OpenApiParameter(
        "stage", OpenApiTypes.STR, enum=[choice for choice, _ in Plant.Stage.choices],
        description="Exact growth stage.",
    ),
    OpenApiParameter(
        "ordering", OpenApiTypes.STR, enum=list(ORDERING_FIELDS),
        description="Sort order (default `-created_at`, newest first).",
    ),
]


@extend_schema_view(
    list=extend_schema(tags=["my-plants"], summary="List my plants", parameters=LIST_PARAMETERS),
    retrieve=extend_schema(tags=["my-plants"], summary="Plant detail"),
    create=extend_schema(tags=["my-plants"], summary="Add a planted plant"),
    update=extend_schema(tags=["my-plants"], summary="Edit a plant"),
    partial_update=extend_schema(tags=["my-plants"], summary="Edit some fields of a plant"),
    destroy=extend_schema(
        tags=["my-plants"],
        summary="Delete a plant",
        description="Returns 409 when the plant still has care tasks or journal entries; mark it Finished instead.",
    ),
)
class MyPlantViewSet(viewsets.ModelViewSet):
    serializer_class = MyPlantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # OpenAPI schema generation, no real user
            return Plant.objects.none()
        queryset = Plant.objects.for_user(self.request.user)
        if self.action != "list":
            return queryset

        params = self.request.query_params
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(species_name__icontains=search))

        status = params.get("status")
        if status == "active":
            queryset = queryset.active()
        elif status == "finished":
            queryset = queryset.filter(growth_stage=Plant.Stage.FINISHED)

        stage = params.get("stage")
        if stage in Plant.Stage.values:
            queryset = queryset.filter(growth_stage=stage)

        ordering = ORDERING_FIELDS.get(params.get("ordering", ""))
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
