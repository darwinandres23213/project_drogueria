from django.urls import path

from apps.inventario.presentation.views.status import module_status

urlpatterns = [
    path('status/', module_status, name='inventario-status'),
]
