from apps.integraciones.domain.repositories import (
    ErrorIntegracionRepository,
    SincronizacionRepository,
)


class DjangoSincronizacionRepository(SincronizacionRepository):
    def crear(self, *, sistema_id, tipo, estado='PENDIENTE'):
        from apps.integraciones.models import Sincronizacion

        return Sincronizacion.objects.create(
            sistema_id=sistema_id,
            tipo=tipo,
            estado=estado,
        )

    def actualizar(self, sincronizacion_id, **campos):
        from apps.integraciones.models import Sincronizacion

        Sincronizacion.objects.filter(pk=sincronizacion_id).update(**campos)
        return Sincronizacion.objects.filter(pk=sincronizacion_id).first()


class DjangoErrorIntegracionRepository(ErrorIntegracionRepository):
    def registrar(self, *, sincronizacion_id, tipo_error, mensaje, payload=None):
        from apps.integraciones.models import ErrorIntegracion

        return ErrorIntegracion.objects.create(
            sincronizacion_id=sincronizacion_id,
            tipo_error=tipo_error,
            mensaje=mensaje,
            payload=payload,
        )
