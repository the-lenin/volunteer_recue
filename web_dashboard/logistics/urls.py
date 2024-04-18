"""
URL configuration for web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # Departures
    path('', views.DepartureListView.as_view(), name='all'),
    path('create/', views.DepartureCreateView.as_view(), name='create'),
    path('<int:pk>/', views.DepartureDetailView.as_view(), name='read'),
    path(
        '<int:pk>/update/',
        views.DepartureUpdateView.as_view(),
        name='update'
    ),
    path(
        '<int:pk>/delete/',
        views.DepartureDeleteView.as_view(),
        name='delete'
    ),
]
