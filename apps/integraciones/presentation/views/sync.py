from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.catalogo.models import Producto
from apps.integraciones.application.services.name_matcher import (
    decide_match,
    normalize_brand_key,
)
from apps.integraciones.application.use_cases import (
    ResolverMatchImagen,
    SincronizarCatalogo,
    SincronizarImagenes,
)
from apps.integraciones.domain.exceptions import (
    IntegracionError,
    ValidacionDatosIntegracionError,
)
from apps.integraciones.infrastructure.models import (
    ImagenMatchPendiente,
    Sincronizacion,
)
from apps.integraciones.presentation.serializers import (
    ImagenMatchSerializer,
    MatchPreviewSerializer,
    ResolverMatchSerializer,
    SincronizacionSerializer,
    SyncCatalogoSerializer,
    SyncImagenesSerializer,
)


def _error_response(exc: Exception):
    if isinstance(exc, IntegracionError):
        code = status.HTTP_400_BAD_REQUEST
        if 'credenciales' in exc.message.lower() or 'onedrive' in exc.message.lower():
            code = status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {'detail': exc.message, 'codigo': exc.codigo, 'payload': exc.payload},
            status=code,
        )
    return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def sync_catalogo(request):
    """
    POST /api/integraciones/sync/catalogo/
    body: force=true|false, optional file= excel
    """
    serializer = SyncCatalogoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    upload = request.FILES.get('archivo') or request.FILES.get('file')
    try:
        result = SincronizarCatalogo().execute(
            force=serializer.validated_data.get('force', False),
            archivo_bytes=upload.read() if upload else None,
            filename=upload.name if upload else 'catalogo.xlsx',
        )
        return Response(result, status=status.HTTP_200_OK)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@api_view(['POST'])
def sync_imagenes(request):
    """
    POST /api/integraciones/sync/imagenes/
    body: { "force": false, "carpeta_local": "C:/..." }
    """
    serializer = SyncImagenesSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    carpeta = serializer.validated_data.get('carpeta_local') or None
    try:
        result = SincronizarImagenes().execute(
            force=serializer.validated_data.get('force', False),
            carpeta_local=carpeta or None,
            max_folders=serializer.validated_data.get('max_folders'),
        )
        return Response(result, status=status.HTTP_200_OK)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@api_view(['POST'])
def match_preview(request):
    """Prueba de matching sin persistir."""
    serializer = MatchPreviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    nombre = serializer.validated_data['nombre_archivo']
    marca = serializer.validated_data.get('marca') or ''

    qs = Producto.objects.filter(activo=True)
    if marca:
        key = normalize_brand_key(marca)
        ids = []
        for p in qs.select_related('marca', 'proveedor').iterator():
            keys = []
            if p.marca_id:
                keys.append(normalize_brand_key(p.marca.nombre))
            if p.proveedor_id:
                keys.append(normalize_brand_key(p.proveedor.nombre))
            if any(key in k or k in key for k in keys if k):
                ids.append(p.id)
        qs = qs.filter(id__in=ids)

    productos = [
        (str(i), n, s) for i, n, s in qs.values_list('id', 'nombre', 'sku')[:5000]
    ]
    decision = decide_match(nombre, productos)
    return Response(
        {
            'nombre_archivo': nombre,
            'action': decision.action,
            'nombre_normalizado': decision.nombre_normalizado,
            'best': (
                {
                    'producto_id': decision.best.producto_id,
                    'nombre': decision.best.nombre,
                    'sku': decision.best.sku,
                    'score': decision.best.score,
                }
                if decision.best
                else None
            ),
            'candidatos': [
                {
                    'producto_id': c.producto_id,
                    'nombre': c.nombre,
                    'sku': c.sku,
                    'score': c.score,
                }
                for c in decision.candidates
            ],
        }
    )


class SincronizacionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sincronizacion.objects.select_related('sistema').all()
    serializer_class = SincronizacionSerializer
    filterset_fields = ['tipo', 'estado']
    ordering = ['-fecha_inicio']


class ImagenMatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImagenMatchPendiente.objects.select_related(
        'producto', 'producto_imagen'
    ).all()
    serializer_class = ImagenMatchSerializer
    filterset_fields = ['estado', 'carpeta_marca']
    search_fields = ['nombre_archivo', 'nombre_normalizado', 'carpeta_marca']
    ordering_fields = ['created_at', 'score', 'nombre_archivo']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'], url_path='resolver')
    def resolver(self, request, pk=None):
        serializer = ResolverMatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = ResolverMatchImagen().execute(
                match_id=pk,
                accion=serializer.validated_data['accion'],
                producto_id=serializer.validated_data.get('producto_id'),
            )
            return Response(result)
        except ValidacionDatosIntegracionError as exc:
            return _error_response(exc)
        except Exception as exc:  # noqa: BLE001
            return _error_response(exc)
