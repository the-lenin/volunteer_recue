from django.urls import path
from django.views.decorators import csrf
from . import views


urlpatterns = [
    path('', csrf.csrf_exempt(views.WebhookView.as_view()), name='webhook'),
]
