from django.views import View
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from secrets import compare_digest

import os


class IndexView(LoginRequiredMixin, View):
    """Root index view after logging."""
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        return render(request, 'index.html')


class JsonView(View):
    """Webhook for local PTB (python-telegram-bot)."""

    def get(self, request, *args, **kwargs):
        given_token = request.headers.get("Authorization", "")
        if not compare_digest(given_token,
                              f'access_token {settings.DJANGO_TG_TOKEN}'):
            return HttpResponseForbidden(
                'Incorect webhook token.',
                content_type="text/plain",
            )
        return HttpResponse('Ok, received')

    def post(self, request, *args, **kwargs):
        print(request.body)
