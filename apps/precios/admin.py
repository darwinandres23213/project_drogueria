from django.contrib import admin

from apps.precios import models

for model in [models.ListaPrecio, models.PrecioProducto]:
    admin.site.register(model)
