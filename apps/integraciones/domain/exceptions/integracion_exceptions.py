"""Excepciones de dominio para integraciones (sin Django/HTTP)."""


class IntegracionError(Exception):
    """Error base de integración."""

    def __init__(self, message: str, *, codigo: str | None = None, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.codigo = codigo or self.__class__.__name__
        self.payload = payload or {}


class AutenticacionIntegracionError(IntegracionError):
    """Fallo de autenticación con el sistema externo."""


class ConexionIntegracionError(IntegracionError):
    """No se pudo conectar con el sistema externo."""


class ApiExternaIntegracionError(IntegracionError):
    """El proveedor externo respondió con error."""


class ValidacionDatosIntegracionError(IntegracionError):
    """Datos inválidos durante la sincronización."""


class SincronizacionIntegracionError(IntegracionError):
    """Error en el proceso de sincronización."""


class PersistenciaIntegracionError(IntegracionError):
    """Error al persistir resultados de integración."""
