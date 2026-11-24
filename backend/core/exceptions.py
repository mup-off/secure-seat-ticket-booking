import logging

from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("secureseat")


def safe_exception_handler(exc, context):
    """Clients get a short, safe message; details and stack traces go only to the
    server log (plan, Phase 5: no stack traces in error messages)."""
    request = context.get("request")
    if isinstance(exc, exceptions.PermissionDenied):
        logger.warning(
            "Forbidden",
            extra={"data": {"path": request.path if request else None,
                            "user": getattr(getattr(request, "user", None), "id", None),
                            "reason": str(exc.detail)}},
        )
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, (Http404, exceptions.NotFound)):
            response.data = {"detail": "Not found."}
        return response

    logger.error("Unhandled error", exc_info=exc, extra={"data": {"path": request.path if request else None}})
    return Response({"detail": "Something went wrong. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
