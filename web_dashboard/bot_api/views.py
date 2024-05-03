from functools import wraps
from django.views import View
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.translation import gettext as _
from secrets import compare_digest

from web_dashboard.search_requests.models import SearchRequest
from web_dashboard.logistics.models import Departure


class ApiAuthTokenMixinView(View):
    """PTB (python-telegram-bot) Auth Token Mixin View."""

    @staticmethod
    def api_auth_token_required(view_func):
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

    def post(self, request, *args, **kwargs):
        print(request.body)


class WebhookView(ApiAuthTokenMixinView):
    """Json view."""

    @ApiAuthTokenMixinView.api_auth_token_required
    def get(self, request, *args, **kwargs):
        """Return present quantity of open models."""
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
        return HttpResponse(msg, content_type="text/plain")
