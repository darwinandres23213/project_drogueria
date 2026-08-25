from django.contrib import admin

from apps.catalogo import models

for model in [
    models.Categoria,
    models.Marca,
    models.Proveedor,
    models.UnidadMedida,
    models.Presentacion,
    models.RegistroSanitario,
    models.Producto,
    models.ProductoImagen,
    models.Atributo,
    models.ProductoAtributo,
    models.ProductoRelacionado,
    models.ProductoEquivalente,
]:
    admin.site.register(model)
