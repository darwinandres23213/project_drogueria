from django.contrib import admin

from apps.inventario import models

for model in [models.Sucursal, models.Inventario, models.MovimientoInventario]:
    admin.site.register(model)
