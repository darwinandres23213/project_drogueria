"""Normalización y match fuzzy nombre-archivo ↔ producto (solo para comparar)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    from difflib import SequenceMatcher

    class fuzz:  # type: ignore[no-redef]
        @staticmethod
        def token_set_ratio(a: str, b: str) -> float:
            return SequenceMatcher(None, a, b).ratio() * 100

        @staticmethod
        def token_sort_ratio(a: str, b: str) -> float:
            sa = ' '.join(sorted(a.split()))
            sb = ' '.join(sorted(b.split()))
            return SequenceMatcher(None, sa, sb).ratio() * 100


UNIT_NOISE = re.compile(
    r'\b('
    r'ml|mg|g|kg|mcg|ug|ui|iu|cc|cm|mm|'
    r'tabs?|tabletas?|caps?|capsulas?|comp|comprimidos?|'
    r'viales?|ampollas?|sobres?|gotas?|crema|gel|jarabe|'
    r'und|unid|unidad(es)?'
    r')\b',
    re.IGNORECASE,
)
NON_ALNUM = re.compile(r'[^a-z0-9]+')
MULTI_SPACE = re.compile(r'\s+')
COPY_SUFFIX = re.compile(r'\s*\(\d+\)\s*$')
PROMO_SUFFIX = re.compile(r'\s*\(\d+\s*%?\+?\)\s*$')
ATTACHED_UNIT = re.compile(
    r'(\d+)(gr|gramos|uds|unds|und|unid|unidades|yd|yardas)\b',
    re.IGNORECASE,
)

ABBREVS = {
    'uds': 'unidades',
    'unds': 'unidades',
    'und': 'unidades',
    'unid': 'unidades',
    'unidad': 'unidades',
    'yd': 'yardas',
    'yds': 'yardas',
    'gr': 'gramos',
    'jbe': 'jarabe',
    'fco': 'frasco',
    'frasco': 'frasco',
    'sol': 'solucion',
    'oft': 'oftalmica',
    'oftal': 'oftalmica',
    'shapoo': 'shampoo',
    'shampoo': 'shampoo',
    'champu': 'shampoo',
}

STOP_TOKENS = {
    'de',
    'del',
    'la',
    'el',
    'los',
    'las',
    'y',
    'e',
    'con',
    'para',
    'en',
    'x',
    'por',
    'sa',
    'sas',
    'ltda',
    'ml',
    'mg',
    'gramos',
    'unidades',
    'tabletas',
    'capsulas',
}

# Auto-asignar si score >= umbral y margen vs 2.º candidato
AUTO_SCORE_MIN = 88.0
AUTO_SCORE_MARGIN = 4.0
# Por debajo de esto ni siquiera entra a cola (ruido)
PENDING_SCORE_MIN = 55.0
SKU_MIN_LEN = 6


def _strip_copy_suffix(value: str) -> str:
    text = COPY_SUFFIX.sub('', value or '')
    return PROMO_SUFFIX.sub('', text).strip()


def _expand_abbrevs(text: str) -> str:
    def _replace_attached(match: re.Match[str]) -> str:
        number, unit = match.group(1), match.group(2).lower()
        return f'{number} {ABBREVS.get(unit, unit)}'

    text = ATTACHED_UNIT.sub(_replace_attached, text)
    return ' '.join(ABBREVS.get(tok, tok) for tok in text.split())


def normalize_for_match(value: str, *, strip_units: bool = False) -> str:
    """Normaliza texto solo para comparación; no altera nombres persistidos."""
    if not value:
        return ''
    text = _strip_copy_suffix(str(value)).strip().casefold()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace('_', ' ')
    if strip_units:
        text = UNIT_NOISE.sub(' ', text)
    text = NON_ALNUM.sub(' ', text)
    text = MULTI_SPACE.sub(' ', text).strip()
    return _expand_abbrevs(text)


def filename_stem(filename: str) -> str:
    return _strip_copy_suffix(Path(filename).stem)


def _distinctive_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for tok in normalize_for_match(value).split():
        if tok in STOP_TOKENS or len(tok) < 2:
            continue
        if tok.isdigit():
            if int(tok) >= 8:
                tokens.add(tok)
            continue
        tokens.add(tok)
    return tokens


def _significant_numbers(value: str) -> set[str]:
    return {
        tok
        for tok in normalize_for_match(value).split()
        if tok.isdigit() and int(tok) >= 8
    }


def _token_f1(left: str, right: str) -> float:
    a = _distinctive_tokens(left)
    b = _distinctive_tokens(right)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    precision = inter / len(a)
    recall = inter / len(b)
    return 2 * precision * recall / (precision + recall)


def similarity_score(left: str, right: str) -> float:
    a = normalize_for_match(left)
    b = normalize_for_match(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    raw = max(
        float(fuzz.token_set_ratio(a, b)),
        float(fuzz.token_sort_ratio(a, b)),
    )
    if raw < PENDING_SCORE_MIN:
        a2 = normalize_for_match(left, strip_units=True)
        b2 = normalize_for_match(right, strip_units=True)
        if a2 and b2:
            raw = max(
                raw,
                float(fuzz.token_set_ratio(a2, b2)),
                float(fuzz.token_sort_ratio(a2, b2)),
            )
    coverage = _token_f1(left, right) * 100
    score = (0.55 * raw) + (0.45 * coverage)
    left_nums = _significant_numbers(left)
    right_nums = _significant_numbers(right)
    if left_nums and right_nums and left_nums.isdisjoint(right_nums):
        score = min(score, 80.0)
    return round(score, 2)


@dataclass(frozen=True)
class MatchCandidate:
    producto_id: str
    nombre: str
    sku: str
    score: float


@dataclass(frozen=True)
class MatchDecision:
    """Resultado de intentar vincular un archivo a un producto."""

    action: str  # auto | pending | skip
    best: MatchCandidate | None
    candidates: tuple[MatchCandidate, ...]
    nombre_normalizado: str


def rank_candidates(
    archivo_nombre: str,
    productos: Iterable[tuple[str, str, str]],
    *,
    limit: int = 5,
) -> list[MatchCandidate]:
    """
    productos: iterable de (producto_id, nombre, sku)
    """
    stem = filename_stem(archivo_nombre)
    ranked: list[MatchCandidate] = []
    for producto_id, nombre, sku in productos:
        score = similarity_score(stem, nombre)
        if sku and len(normalize_for_match(sku)) >= SKU_MIN_LEN:
            score = max(score, similarity_score(stem, sku))
        if score < PENDING_SCORE_MIN:
            continue
        ranked.append(
            MatchCandidate(
                producto_id=str(producto_id),
                nombre=nombre,
                sku=sku,
                score=round(score, 2),
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]


def decide_match(
    archivo_nombre: str,
    productos: Sequence[tuple[str, str, str]],
) -> MatchDecision:
    candidates = tuple(rank_candidates(archivo_nombre, productos))
    normalized = normalize_for_match(filename_stem(archivo_nombre))
    if not candidates:
        return MatchDecision(
            action='skip',
            best=None,
            candidates=(),
            nombre_normalizado=normalized,
        )

    exact = [
        c
        for c in candidates
        if normalize_for_match(c.nombre) == normalized
    ]
    if exact:
        return MatchDecision(
            action='auto',
            best=exact[0],
            candidates=candidates,
            nombre_normalizado=normalized,
        )

    best = candidates[0]
    second = next(
        (c for c in candidates[1:] if normalize_for_match(c.nombre) != normalize_for_match(best.nombre)),
        None,
    )
    second_score = second.score if second is not None else 0.0
    margin = best.score - second_score

    if best.score >= AUTO_SCORE_MIN and margin >= AUTO_SCORE_MARGIN:
        return MatchDecision(
            action='auto',
            best=best,
            candidates=candidates,
            nombre_normalizado=normalized,
        )

    return MatchDecision(
        action='pending',
        best=best,
        candidates=candidates,
        nombre_normalizado=normalized,
    )


def normalize_brand_key(value: str) -> str:
    """Clave corta para alias de carpetas/marcas (3.M / *3.m / 3M)."""
    text = normalize_for_match(value)
    text = text.replace(' ', '')
    for noise in ('sas', 'sa', 'ltda', 'ltd', 'inc', 'colombia', 'delatinamerica'):
        if text.endswith(noise) and len(text) > len(noise) + 2:
            text = text[: -len(noise)]
    return text


def distinctive_tokens(value: str) -> set[str]:
    return _distinctive_tokens(value)


# Aliases for older tests/imports
decide_match = decide_match  # noqa: F811
normalize_brand_key = normalize_brand_key
similarity_score = similarity_score
normalize_for_match = normalize_for_match
