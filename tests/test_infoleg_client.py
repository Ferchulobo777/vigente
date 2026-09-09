from ingest.infoleg_client import extract_articles

_SAMPLE_HTML = """
<html><body>
<div>VISTO tal cosa, CONSIDERANDO tal otra,<br>RESUELVE:<br></div>
ARTÍCULO 1°.- Este es el primer artículo, con &#8220;comillas&#8221; y una lista:<br>
a) primer item<br>
b) segundo item<br>
<br>
ARTÍCULO 2°.- Este es el segundo artículo.<br>
<br>
ARTÍCULO 10.- Los artículos de dos dígitos no llevan el símbolo °.<br>
</body></html>
"""


def test_extract_articles_ignores_preamble_before_first_article():
    articles = extract_articles(_SAMPLE_HTML)
    assert "VISTO" not in articles[0].content
    assert "RESUELVE" not in articles[0].content


def test_extract_articles_splits_by_article_number():
    articles = extract_articles(_SAMPLE_HTML)
    labels = [a.label for a in articles]
    assert labels == ["Artículo 1°", "Artículo 2°", "Artículo 10°"]


def test_extract_articles_unescapes_html_entities():
    articles = extract_articles(_SAMPLE_HTML)
    assert "“comillas”" in articles[0].content


def test_extract_articles_stops_at_next_article():
    articles = extract_articles(_SAMPLE_HTML)
    assert "segundo artículo" not in articles[0].content
    assert "primer artículo" in articles[0].content


def test_extract_articles_handles_two_digit_numbers_without_degree_symbol():
    """Verificado contra la RG 4309 real: "ARTÍCULO 1°.-" lleva el símbolo °,
    pero "ARTÍCULO 10.-" no — un patrón que exigiera ° siempre perdería en
    silencio todo artículo de dos dígitos o más."""
    articles = extract_articles(_SAMPLE_HTML)
    assert any(a.label == "Artículo 10°" for a in articles)
