"""Global error handling for the mobile REST API (/api/v1/).

Every API error is JSON with the same shape, so the Flutter client can
handle all modules the same way:

    {"detail": "<message>", "status_code": 404}
    {"planted_on": ["..."], "status_code": 400}          # serializer errors

Unexpected exceptions never leak an HTML debug page or a traceback.
"""
import logging

from django.db.models import ProtectedError
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("terrapeer.api")


def api_exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response(
            {
                "detail": "This item is still used by other records and cannot be deleted.",
                "status_code": status.HTTP_409_CONFLICT,
            },
            status=status.HTTP_409_CONFLICT,
        )

    response = exception_handler(exc, context)
    if response is None:
        view = context.get("view")
        logger.exception("Unhandled API error in %s", view.__class__.__name__ if view else "?")
        return Response(
            {"detail": "Internal server error.", "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = response.data
    if isinstance(data, list):
        data = {"non_field_errors": data}
    elif not isinstance(data, dict):
        data = {"detail": str(data)}
    data["status_code"] = response.status_code
    response.data = data
    return response


def api_not_found(request, *args, **kwargs):
    """JSON 404 for unknown /api/v1/ paths (instead of the HTML 404 page)."""
    return JsonResponse(
        {"detail": "Not found.", "status_code": status.HTTP_404_NOT_FOUND},
        status=status.HTTP_404_NOT_FOUND,
    )
