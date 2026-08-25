from django.contrib import admin

from apps.ventas import models

for model in [
    models.Cliente,
    models.DireccionCliente,
    models.Cupon,
    models.Pedido,
    models.DetallePedido,
]:
    admin.site.register(model)
