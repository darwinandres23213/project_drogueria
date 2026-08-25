"""Reevalúa matches PENDIENTE y vincula los que ahora califican como auto."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from apps.catalogo.models import Producto
from apps.integraciones.application.services.name_matcher import (
    decide_match,
    distinctive_tokens,
    normalize_for_match,
)
from apps.integraciones.application.services.sync_helpers import (
    candidates_payload,
    link_product_image,
    mark_match_linked,
    sync_paths_from_settings,
)
from apps.integraciones.application.use_cases.sincronizar_imagenes import (
    SincronizarImagenes,
)
from apps.integraciones.infrastructure.external.local_fs import LocalFilesystemProvider
from apps.integraciones.infrastructure.models import ImagenMatchPendiente


class VincularImagenesPendientes:
    def execute(self, *, dry_run: bool = False) -> dict[str, Any]:
        stats = {
            'revisados': 0,
            'vinculados': 0,
            'duplicados': 0,
            'siguen_pendientes': 0,
            'sin_url': 0,
            'errores': 0,
            'dry_run': dry_run,
        }
        sync = SincronizarImagenes()
        brand_index = sync._build_brand_index()
        all_products = [
            (str(i), n, s)
            for i, n, s in Producto.objects.filter(activo=True).values_list(
                'id', 'nombre', 'sku'
            )
        ]
        token_index = _build_token_index(all_products)

        pending = ImagenMatchPendiente.objects.filter(
            estado=ImagenMatchPendiente.Estado.PENDIENTE
        )
        for match in pending.iterator():
            stats['revisados'] += 1
            try:
                if _is_folder_banner(match):
                    stats['siguen_pendientes'] += 1
                    continue

                productos = sync._products_for_folder(
                    match.carpeta_marca, brand_index
                )
                decision = decide_match(match.nombre_archivo, productos)
                if decision.action != 'auto':
                    pooled = _products_for_tokens(
                        match.nombre_archivo, token_index, all_products
                    )
                    if pooled:
                        decision = decide_match(match.nombre_archivo, pooled)

                if decision.action != 'auto' or decision.best is None:
                    stats['siguen_pendientes'] += 1
                    continue

                url = (match.url_origen or '').strip()
                if not url:
                    url = _public_url_for(match.ruta_remota)
                if not url:
                    stats['sin_url'] += 1
                    continue

                if dry_run:
                    stats['vinculados'] += 1
                    continue

                producto = Producto.objects.get(pk=decision.best.producto_id)
                imagen = link_product_image(
                    producto=producto,
                    url_imagen=url,
                    origen_remoto=match.ruta_remota,
                )
                match.nombre_normalizado = decision.nombre_normalizado
                match.score = Decimal(str(decision.best.score))
                match.candidatos = candidates_payload(decision.candidates)
                match.url_origen = url
                match.save(
                    update_fields=[
                        'nombre_normalizado',
                        'score',
                        'candidatos',
                        'url_origen',
                        'updated_at',
                    ]
                )
                mark_match_linked(
                    match,
                    producto=producto,
                    imagen=imagen,
                    estado=ImagenMatchPendiente.Estado.AUTO,
                )
                extras = _link_same_name_duplicates(
                    best_name=producto.nombre,
                    url=url,
                    origen=match.ruta_remota,
                    already_id=str(producto.id),
                    candidates=decision.candidates,
                )
                stats['vinculados'] += 1
                stats['duplicados'] += extras
            except Exception:  # noqa: BLE001
                stats['errores'] += 1
        return stats


def _is_folder_banner(match: ImagenMatchPendiente) -> bool:
    stem = Path(match.nombre_archivo).stem
    folder = match.carpeta_marca or ''
    if not folder:
        return False
    return normalize_for_match(stem) == normalize_for_match(folder)


def _build_token_index(
    productos: list[tuple[str, str, str]],
) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for producto_id, nombre, _sku in productos:
        for token in distinctive_tokens(nombre):
            index[token].append(producto_id)
    return index


def _products_for_tokens(
    filename: str,
    token_index: dict[str, list[str]],
    all_products: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    tokens = distinctive_tokens(filename)
    if not tokens:
        return []
    ids: set[str] = set()
    for token in tokens:
        ids.update(token_index.get(token, ()))
    if not ids:
        return []
    by_id = {row[0]: row for row in all_products}
    return [by_id[i] for i in ids if i in by_id]


def _public_url_for(ruta_remota: str) -> str:
    paths = sync_paths_from_settings()
    local = paths.get('imagenes_local') or ''
    if not local or not Path(local).exists() or not ruta_remota:
        return ''
    provider = LocalFilesystemProvider(local)
    return provider.public_url_for(ruta_remota) or ''


def _link_same_name_duplicates(
    *,
    best_name: str,
    url: str,
    origen: str,
    already_id: str,
    candidates,
) -> int:
    target = normalize_for_match(best_name)
    extra = 0
    seen = {already_id}
    for cand in candidates:
        if cand.producto_id in seen:
            continue
        if normalize_for_match(cand.nombre) != target:
            continue
        producto = Producto.objects.filter(pk=cand.producto_id, activo=True).first()
        if producto is None:
            continue
        if producto.imagenes.filter(es_principal=True).exists():
            continue
        link_product_image(
            producto=producto,
            url_imagen=url,
            origen_remoto=origen,
        )
        seen.add(cand.producto_id)
        extra += 1
    return extra
