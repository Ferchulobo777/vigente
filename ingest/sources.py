"""Fuentes reales del corpus — cada una verificada a mano antes de agregarse.

Ampliar el corpus (nuevas modificatorias, otros regímenes) es agregar una
entrada acá, no reescribir el pipeline. Ver CLAUDE.md sobre por qué el
alcance está acotado a Monotributo y no a "toda la normativa de ARCA".
"""

import datetime as dt
from dataclasses import dataclass


@dataclass
class InfoLegSource:
    source_id: str
    title: str
    url: str
    published_at: dt.date


@dataclass
class ScaleRow:
    category: str
    annual_income_cap: float
    services_quota: float
    goods_quota: float


INFOLEG_SOURCES: list[InfoLegSource] = [
    InfoLegSource(
        source_id="infoleg-314485",
        title="Resolución General 4309/2018 (AFIP) — Régimen Simplificado para Pequeños Contribuyentes",
        url="https://servicios.infoleg.gob.ar/infolegInternet/anexos/310000-314999/314485/norma.htm",
        published_at=dt.date(2018, 9, 17),
    ),
]

# Tabla de categorías vigente desde 1/08/2026, tomada directamente de
# https://www.afip.gob.ar/monotributo/categorias.asp — se actualiza por
# resolución cada vez que ARCA ajusta los montos (típicamente cada 6 meses).
# Repetir esta captura es el único mantenimiento periódico que este corpus
# necesita; ver CLAUDE.md.
MONOTRIBUTO_SCALE_SOURCE_ID = "arca-categorias-2026-08"
MONOTRIBUTO_SCALE_TITLE = "Categorías de Monotributo vigentes desde el 1/08/2026 (ARCA)"
MONOTRIBUTO_SCALE_URL = "https://www.afip.gob.ar/monotributo/categorias.asp"
MONOTRIBUTO_SCALE_PUBLISHED_AT = dt.date(2026, 8, 1)

MONOTRIBUTO_SCALE: list[ScaleRow] = [
    ScaleRow("A", 12_009_410.45, 49_527.18, 49_527.18),
    ScaleRow("B", 17_595_182.74, 56_379.08, 56_379.08),
    ScaleRow("C", 24_670_494.31, 66_020.12, 64_530.58),
    ScaleRow("D", 30_628_651.43, 84_612.93, 82_564.81),
    ScaleRow("E", 36_028_231.33, 119_811.45, 108_267.51),
    ScaleRow("F", 45_151_659.41, 150_784.21, 129_930.65),
    ScaleRow("G", 53_995_798.87, 230_312.94, 158_815.05),
    ScaleRow("H", 81_924_660.37, 522_706.68, 317_895.01),
    ScaleRow("I", 91_699_761.90, 963_747.86, 474_992.78),
    ScaleRow("J", 105_012_519.20, 1_167_299.76, 580_793.69),
    ScaleRow("K", 126_610_838.75, 1_614_446.04, 702_103.24),
]


def _format_ars(amount: float) -> str:
    """Formatea con separador de miles '.' y decimales ',', como en Argentina."""
    us_format = f"{amount:,.2f}"  # ej. "12,009,410.45"
    return us_format.replace(",", "_").replace(".", ",").replace("_", ".")


def scale_row_to_chunk_text(row: ScaleRow) -> str:
    return (
        f"Categoría {row.category}: tope de ingresos brutos anuales "
        f"${_format_ars(row.annual_income_cap)}. Cuota mensual para locación o "
        f"prestación de servicios: ${_format_ars(row.services_quota)}. Cuota mensual "
        f"para venta de bienes muebles: ${_format_ars(row.goods_quota)}."
    )
