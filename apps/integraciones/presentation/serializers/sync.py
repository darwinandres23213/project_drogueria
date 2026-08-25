from rest_framework import serializers

from apps.integraciones.infrastructure.models import (
    ErrorIntegracion,
    ImagenMatchPendiente,
    Sincronizacion,
)


class SincronizacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sincronizacion
        fields = [
            'id',
            'sistema',
            'tipo',
            'estado',
            'fecha_inicio',
            'fecha_fin',
            'registros_procesados',
            'registros_exitosos',
            'registros_error',
        ]
        read_only_fields = fields


class ErrorIntegracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorIntegracion
        fields = [
            'id',
            'sincronizacion',
            'tipo_error',
            'mensaje',
            'payload',
            'created_at',
        ]
        read_only_fields = fields


class ImagenMatchSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(
        source='producto.nombre', read_only=True, allow_null=True
    )
    producto_sku = serializers.CharField(
        source='producto.sku', read_only=True, allow_null=True
    )

    class Meta:
        model = ImagenMatchPendiente
        fields = [
            'id',
            'ruta_remota',
            'nombre_archivo',
            'carpeta_marca',
            'url_origen',
            'nombre_normalizado',
            'score',
            'candidatos',
            'estado',
            'producto',
            'producto_nombre',
            'producto_sku',
            'producto_imagen',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ResolverMatchSerializer(serializers.Serializer):
    accion = serializers.ChoiceField(choices=['aceptar', 'rechazar'])
    producto_id = serializers.UUIDField(required=False, allow_null=True)


class SyncCatalogoSerializer(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)
    # archivo se toma de request.FILES


class SyncImagenesSerializer(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)
    carpeta_local = serializers.CharField(required=False, allow_blank=True)
    max_folders = serializers.IntegerField(required=False, min_value=1)


class MatchPreviewSerializer(serializers.Serializer):
    nombre_archivo = serializers.CharField()
    marca = serializers.CharField(required=False, allow_blank=True)
