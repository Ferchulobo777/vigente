"""Cliente para descargar y parsear el texto completo de normas de InfoLeg.

InfoLeg publica el texto completo en HTML sin estructura semántica (sin
<article>/<section>, todo separado por <br>) y codificado en ISO-8859-1, no
UTF-8 — verificado a mano contra la página real de la RG 4309/2018 antes de
escribir este parser (ver CLAUDE.md, sección "Fuentes de datos"). El patrón
de los artículos es "ARTÍCULO 4°.- texto..." hasta el próximo "ARTÍCULO N".
"""

import html
import re
from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_ARTICLE_PATTERN = re.compile(r"ART[ÍI]CULO\s+(\d+)[°ºo]?\.-", re.IGNORECASE)


@dataclass
class Article:
    label: str
    content: str


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def fetch_raw_html(url: str) -> str:
    response = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20, follow_redirects=True)
    response.raise_for_status()
    # InfoLeg declara ISO-8859-1 en el <meta charset> pero httpx asume UTF-8
    # por defecto si no hay header Content-Type explícito con charset — sin
    # este decode manual, las tildes y "ñ" salen corruptas.
    return response.content.decode("iso-8859-1")


def _strip_tags_preserve_breaks(raw_html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def extract_articles(raw_html: str) -> list[Article]:
    """Extrae cada ARTÍCULO como un chunk citable independiente.

    Todo lo anterior al primer ARTÍCULO (VISTO/CONSIDERANDO, los fundamentos
    de la norma) se descarta a propósito: no es texto operativo, y citarlo
    como si fuera una obligación induciría a error.
    """
    text = _strip_tags_preserve_breaks(raw_html)
    matches = list(_ARTICLE_PATTERN.finditer(text))
    articles: list[Article] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        body = re.sub(r"\n{2,}", "\n\n", body).strip()
        if not body:
            continue
        articles.append(Article(label=f"Artículo {match.group(1)}°", content=body))
    return articles
