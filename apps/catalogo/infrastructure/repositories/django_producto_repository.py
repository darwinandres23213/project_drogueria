from apps.catalogo.domain.repositories import ProductoRepository


class DjangoProductoRepository(ProductoRepository):
    """Adaptador ORM — implementación se completará con las HU de catálogo."""

    def get_by_id(self, producto_id):
        from apps.catalogo.models import Producto

        return Producto.objects.filter(pk=producto_id).first()

    def get_by_sku(self, sku):
        from apps.catalogo.models import Producto

        return Producto.objects.filter(sku=sku).first()

    def list_activos(self):
        from apps.catalogo.models import Producto

        return Producto.objects.filter(activo=True)
