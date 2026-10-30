"""Account quotas use the shared DB rather than IP headers or a worker-local cache."""
import time
from functools import wraps

from django.db import transaction
from django.http import HttpResponse, JsonResponse

from .models import RequestQuota


def account_rate_limit(scope, limit=30, seconds=60, methods=('POST',)):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                return view(request, *args, **kwargs)
            now = int(time.time())
            window = now // seconds
            with transaction.atomic():
                quota, _ = RequestQuota.objects.select_for_update().get_or_create(user=request.user, scope=scope)
                if quota.window != window:
                    quota.window, quota.hits = window, 0
                allowed = quota.hits < limit
                if allowed:
                    quota.hits += 1
                    quota.save(update_fields=['window', 'hits'])
            if not allowed:
                error = 'Too many requests. Please wait a moment and try again.'
                response = (JsonResponse({'error': error}, status=429)
                            if 'application/json' in request.headers.get('Accept', '') or scope == 'species'
                            else HttpResponse(error, status=429, content_type='text/plain'))
                response['Retry-After'] = str(seconds - now % seconds)
                response['Cache-Control'] = 'no-store'
                return response
            return view(request, *args, **kwargs)
        return wrapped
    return decorate
