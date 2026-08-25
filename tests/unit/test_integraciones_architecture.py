from django.test import SimpleTestCase

from apps.integraciones.domain.repositories import StorageProvider
from apps.integraciones.infrastructure.container import get_storage_provider
from apps.integraciones.infrastructure.external.onedrive import OneDriveClient


class StorageProviderArchitectureTests(SimpleTestCase):
    def test_onedrive_client_implements_storage_provider(self):
        self.assertTrue(issubclass(OneDriveClient, StorageProvider))

    def test_container_returns_storage_provider(self):
        provider = get_storage_provider()
        self.assertIsInstance(provider, StorageProvider)


class DomainExceptionsTests(SimpleTestCase):
    def test_integracion_error_carries_codigo(self):
        from apps.integraciones.domain.exceptions import AutenticacionIntegracionError

        err = AutenticacionIntegracionError('fallo', codigo='AUTH')
        self.assertEqual(err.codigo, 'AUTH')
        self.assertEqual(err.message, 'fallo')
