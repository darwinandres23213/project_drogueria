from django.core.management.base import BaseCommand

from apps.integraciones.application.use_cases.sincronizar_imagenes import SincronizarImagenes


class Command(BaseCommand):
    help = (
        'Empareja el nombre del producto con el archivo de imagen en disco '
        'y guarda la ruta pública (/media/imagenes-productos/...).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reprocesa aunque el fingerprint de la carpeta no haya cambiado.',
        )
        parser.add_argument(
            '--carpeta',
            type=str,
            default='',
            help='Ruta absoluta a la carpeta de imágenes (opcional).',
        )

    def handle(self, *args, **options):
        carpeta = options.get('carpeta') or None
        result = SincronizarImagenes().execute(
            force=bool(options.get('force')),
            carpeta_local=carpeta,
        )
        self.stdout.write(self.style.SUCCESS(str(result)))
