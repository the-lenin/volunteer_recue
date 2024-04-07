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

app_name = 'search_requests'

urlpatterns = [
    # Search Requests
    path('', views.SearchRequestListView.as_view(), name='all'),
    path('create/', views.SearchResquestCreateView.as_view(), name='create'),
    path('<int:pk>/', views.SearchRequestDetailView.as_view(), name='read'),
    path(
        '<int:pk>/update/',
        views.SearchRequestUpdateView.as_view(),
        name='update'
    ),
    path(
        '<int:pk>/delete/',
        views.SearchRequestDeleteView.as_view(),
        name='delete'
    ),

    # Surveys
    path(
        '<int:pk>/sv/create/',
        views.SurveyCreateView.as_view(),
        name='sv_create'
    ),
    path(
        'sv/<int:pk>/',
        views.SurveyDetailView.as_view(),
        name='sv_read'
    ),
    path(
        'sv/<int:pk>/update/',
        views.SurveyUpdateView.as_view(),
        name='sv_update'
    ),
    path(
        'sv/<int:pk>/delete/',
        views.SurveyDeleteView.as_view(),
        name='sv_delete'
    ),
]
