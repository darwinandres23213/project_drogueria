from django.core.management.base import BaseCommand

from apps.integraciones.application.use_cases.vincular_imagenes_pendientes import (
    VincularImagenesPendientes,
)


class Command(BaseCommand):
    help = (
        'Reevalúa la cola PENDIENTE y vincula imágenes con match automático seguro.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo cuenta cuántos se vincularían, sin escribir.',
        )

    def handle(self, *args, **options):
        result = VincularImagenesPendientes().execute(
            dry_run=bool(options.get('dry_run')),
        )
        self.stdout.write(self.style.SUCCESS(str(result)))
