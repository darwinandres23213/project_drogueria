from django.urls import path

from apps.ventas.presentation.views.status import module_status

urlpatterns = [
    path('status/', module_status, name='ventas-status'),
]
