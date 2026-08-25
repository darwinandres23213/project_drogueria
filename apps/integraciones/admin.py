from django.contrib import admin

from apps.integraciones import models

for model in [
    models.SistemaIntegracion,
    models.IntegracionProducto,
    models.Sincronizacion,
    models.ErrorIntegracion,
    models.VentaExterna,
]:
    admin.site.register(model)
