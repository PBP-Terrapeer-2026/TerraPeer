"""Plant Care: tugas hanya untuk Plant milik user dan hanya pending yang bisa diedit."""
from django.http import Http404
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from my_plants.models import Plant
from .models import CareTask
from .services import complete_task, undo_completion, UndoCompletionConflict


class CareTaskSerializer(serializers.ModelSerializer):
    plant = serializers.PrimaryKeyRelatedField(queryset=Plant.objects.none())

    class Meta:
        model = CareTask
        fields = (
            "id", "plant", "title", "action_type", "due_date", "repeat_every",
            "instructions", "status", "completed_at",
        )
        read_only_fields = ("id", "status", "completed_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["plant"].queryset = Plant.objects.for_user(request.user).active()
        # Saat edit tugas pending, tanaman asal boleh tetap dipakai bahkan jika sudah finished.
        if isinstance(self.instance, CareTask) and self.instance.plant_id:
            self.fields["plant"].queryset = Plant.objects.filter(pk=self.instance.plant_id) | self.fields["plant"].queryset


class CareTaskViewSet(viewsets.ModelViewSet):
    serializer_class = CareTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CareTask.objects.filter(plant__owner=self.request.user, plant__isnull=False).select_related("plant")

    def perform_update(self, serializer):
        if serializer.instance.status == "Completed":
            raise serializers.ValidationError({"detail": "Completed tasks cannot be edited."})
        serializer.save()

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        try:
            task, following, changed = complete_task(task.pk, request.user)
        except (CareTask.DoesNotExist, OverflowError):
            return Response({"detail": "Task could not be completed."}, status=status.HTTP_409_CONFLICT)
        return Response({"completed": changed, "next_id": following.pk if following else None,
                         "task": self.get_serializer(task).data})

    @action(detail=True, methods=["post"])
    def undo(self, request, pk=None):
        task = self.get_object()
        try:
            task, changed = undo_completion(task.pk, request.user)
        except (CareTask.DoesNotExist, UndoCompletionConflict, OverflowError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({"undone": changed, "task": self.get_serializer(task).data})
