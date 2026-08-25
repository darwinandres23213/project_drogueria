from apps.inventario.domain.repositories import InventarioRepository


class DjangoInventarioRepository(InventarioRepository):
    def get_by_producto_sucursal(self, producto_id, sucursal_id):
        from apps.inventario.models import Inventario

        return Inventario.objects.filter(producto_id=producto_id, sucursal_id=sucursal_id).first()

    def list_by_sucursal(self, sucursal_id):
        from apps.inventario.models import Inventario

        return Inventario.objects.filter(sucursal_id=sucursal_id)
