import json

from functools import wraps
from django.views import View
from django.conf import settings
from django.core import serializers
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils.translation import gettext as _
from secrets import compare_digest

from web_dashboard.search_requests.models import SearchRequest
from web_dashboard.logistics.models import Departure
from web_dashboard.logistics.serializers import DepartureSerializer


class AuthTokenMixinView(View):
    """PTB (python-telegram-bot) Auth Token Mixin View."""

    @staticmethod
    def auth_token_required(view_func):
        """Decorator adds API token validation."""

        @wraps(view_func)
        def _wrapped_func(self, request, *args, **kwargs):
            """
            Execute a func if the token is present in headers, else forbidden.
            """
            given_token = request.headers.get("Authorization", "")

            if not compare_digest(
                given_token, f'access_token {settings.DJANGO_TG_TOKEN}'
            ):

                return HttpResponseForbidden(
                    'Incorect webhook token.', content_type="text/plain"
                )

            return view_func(self, request, *args, **kwargs)
        return _wrapped_func


class WebhookView(AuthTokenMixinView):
    """Json view."""

    @AuthTokenMixinView.auth_token_required
    def get(self, request, *args, **kwargs) -> JsonResponse:
        """Return ok msg if request is correctly configured."""
        return JsonResponse({'msg': 'Ok, received'})

    @AuthTokenMixinView.auth_token_required
    def post(self, request, *args, **kwargs):
        payload = json.loads(request.body)
        action = payload.get('action')
        match action:
            case 'info':
                return self.get_info(payload)

            case 'get_open_departures':
                return self.get_open_departures(payload)

    def get_info(self, payload: dict) -> JsonResponse:
        """Return present quantity of open SearchRequests and Departures."""
        search_requests = SearchRequest.objects.filter(
            status=SearchRequest.StatusVerbose.OPEN
        )

        departures = Departure.objects.filter(
            status=Departure.StatusVerbose.OPEN
        )
        msg = (
            f'{SearchRequest._meta.verbose_name_plural}: {len(search_requests)}\n'
            f'{Departure._meta.verbose_name_plural}: {len(departures)}'
        )
        return JsonResponse({'msg': msg})

    def get_open_departures(self, payload):
        open_departures = Departure.objects.filter(
            status=Departure.StatusVerbose.OPEN
        ).prefetch_related('search_request')

        departures = [
            DepartureSerializer(dep).data for dep in open_departures
        ]

        json_response = {
            'msg': 'Ok, received',
            'departures': departures,
        }

        return JsonResponse(json_response)
