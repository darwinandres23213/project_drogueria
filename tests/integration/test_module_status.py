from django.test import TestCase


class ModuleStatusEndpointTests(TestCase):
    def test_catalogo_status(self):
        response = self.client.get('/api/catalogo/status/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['module'], 'catalogo')

    def test_integraciones_status(self):
        response = self.client.get('/api/integraciones/status/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['module'], 'integraciones')
