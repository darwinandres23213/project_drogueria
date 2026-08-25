"""HU-SIG-008 — Registrar error de integración (esqueleto usable)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from apps.integraciones.domain.repositories import ErrorIntegracionRepository


class RegistrarErrorIntegracion:
    def __init__(self, errores: ErrorIntegracionRepository):
        self._errores = errores

    def execute(
        self,
        *,
        sincronizacion_id: UUID,
        tipo_error: str,
        mensaje: str,
        payload: Optional[dict[str, Any]] = None,
    ):
        return self._errores.registrar(
            sincronizacion_id=sincronizacion_id,
            tipo_error=tipo_error,
            mensaje=mensaje,
            payload=payload,
        )
