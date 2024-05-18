from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    # path('create/', views.CustomUserCreateView.as_view(), name='create'),
    # path('<int:pk>/', views.CustomUserDetailView.as_view(), name='read'),
    path(
        'update/',
        views.CustomUserUpdateView.as_view(),
        name='update'
    ),
    path(
        'delete/',
        views.CustomUserDeleteView.as_view(),
        name='delete'
    ),
]
