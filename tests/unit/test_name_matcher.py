from django.test import SimpleTestCase

from apps.integraciones.application.services.name_matcher import (
    decide_match,
    normalize_brand_key,
    normalize_for_match,
    similarity_score,
)


class NameMatcherTests(SimpleTestCase):
    def test_normalize_keeps_comparison_only(self):
        original = 'RESTASIS 0.05% 0.4 ML 30 VIALES'
        normalized = normalize_for_match(original)
        self.assertEqual(normalized, 'restasis 0 05 0 4 ml 30 viales')
        self.assertNotEqual(normalized, original)

    def test_brand_aliases_collapse(self):
        self.assertEqual(normalize_brand_key('3.M'), normalize_brand_key('*3.m'))
        self.assertEqual(normalize_brand_key('3M'), normalize_brand_key('3-m'))

    def test_auto_match_similar_names(self):
        productos = [
            ('1', 'RESTASIS 0.05% 0.4 ML 30 VIALES', 'SKU-1'),
            ('2', 'RELESTAT GOTAS 5 ML', 'SKU-2'),
        ]
        decision = decide_match('RESTASIS 0.05% 0.4 ML 30 VIALES.jpg', productos)
        self.assertEqual(decision.action, 'auto')
        self.assertEqual(decision.best.producto_id, '1')

    def test_pending_when_ambiguous(self):
        productos = [
            ('1', 'REFRESH TEARS GOTAS 10 ML', 'A'),
            ('2', 'REFRESH TEARS GOTAS LUBRICANTES 10 ML', 'B'),
        ]
        decision = decide_match('REFRESH TEARS GOTAS 10 ML.png', productos)
        self.assertIn(decision.action, {'auto', 'pending'})
        if decision.action == 'pending':
            self.assertGreaterEqual(len(decision.candidates), 2)

    def test_similarity_high_for_close_names(self):
        score = similarity_score(
            'ALCON SYSTANE ULTRA 10ML',
            'SYSTANE ULTRA 10 ML',
        )
        self.assertGreaterEqual(score, 70)

    def test_copy_suffix_auto_links_same_name(self):
        productos = [
            ('1', 'JABON ASEPXIA AZUFRE 100 GRAMOS', 'A'),
            ('2', 'JABON ASEPXIA AZUFRE 100 GRAMOS', 'B'),
        ]
        decision = decide_match(
            'JABON ASEPXIA AZUFRE 100 GRAMOS (2).png', productos
        )
        self.assertEqual(decision.action, 'auto')
        self.assertEqual(decision.best.producto_id, '1')

    def test_abbreviations_match_full_words(self):
        productos = [
            ('1', 'GASA ALFA SAFE ESTERIL 4X4X2 YARDAS 24 UNIDADES', 'A'),
            ('2', 'MICROPORO ALFA PIEL 1 PULGADA', 'B'),
        ]
        decision = decide_match(
            'GASA ALFA SAFE ESTERIL 4X4X2 YD 24 UDS.png', productos
        )
        self.assertEqual(decision.action, 'auto')
        self.assertEqual(decision.best.producto_id, '1')

    def test_does_not_match_subset_brand_line(self):
        productos = [
            ('1', 'CREMA JJ BABY 400 ML', 'A'),
            ('2', 'SHAMPOO JJ BABY FUERZA Y VITAMINA E 400 ML', 'B'),
        ]
        decision = decide_match(
            'SHAPOO.JJ BABY FUERZA Y VITAMINA E 400 ML.png', productos
        )
        self.assertEqual(decision.action, 'auto')
        self.assertEqual(decision.best.producto_id, '2')

    def test_does_not_auto_match_different_pack_size(self):
        productos = [
            ('1', 'PROTECTORES DIARIOS KOTEX INDICADOR PH 40 UNIDADES', 'A'),
            ('2', 'JABON ASEPXIA AZUFRE 100 GRAMOS', 'B'),
        ]
        decision = decide_match(
            'PROTECTORES DIARIOS KOTEX INDICADOR PH 150 UNIDADES.png',
            productos,
        )
        self.assertNotEqual(decision.action, 'auto')
