"""Scraper do ZAP Imoveis para venda de apartamentos e casas em Fortaleza.

Saida final do CSV:
listing_id,titulo,apartamento_ou_casa,tipo_imovel,estado,cidade,bairro,rua,numero,endereco,metragem,quartos,banheiros,suites,andar,estacionamentos,preco_anuncio,latitude,longitude,tem_portaria_24h,tem_vista_pro_mar,tem_condominio_fechado,tem_piscina,tem_deck,tem_varanda,tem_academia,tem_salao_festas,tem_salao_jogos,tem_quadra_campo,descricao,anuncio_criado,corretora,nota_media,url,imagem_url

O site bloqueia requests diretos, entao este scraper usa Playwright.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse


BASE_URL = "https://www.zapimoveis.com.br"
SEARCH_URLS = {
    "apartamento": "https://www.zapimoveis.com.br/venda/apartamentos/ce%2Bfortaleza/",
    "casa": "https://www.zapimoveis.com.br/venda/casas/ce%2Bfortaleza/",
}

OUTPUT_COLUMNS = [
    "listing_id",
    "titulo",
    "apartamento_ou_casa",
    "tipo_imovel",
    "estado",
    "cidade",
    "bairro",
    "rua",
    "numero",
    "endereco",
    "metragem",
    "quartos",
    "banheiros",
    "suites",
    "andar",
    "estacionamentos",
    "preco_anuncio",
    "latitude",
    "longitude",
    "tem_portaria_24h",
    "tem_vista_pro_mar",
    "tem_condominio_fechado",
    "tem_piscina",
    "tem_deck",
    "tem_varanda",
    "tem_academia",
    "tem_salao_festas",
    "tem_salao_jogos",
    "tem_quadra_campo",
    "descricao",
    "anuncio_criado",
    "corretora",
    "nota_media",
    "url",
    "imagem_url",
]


def _ensure_playwright() -> None:
    try:
        import playwright  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Playwright nao esta instalado. Instale com `pip install playwright` "
            "e depois rode `playwright install chromium`."
        ) from exc


def _clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize(text: str) -> str:
    text = html.unescape(text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def _to_number(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:[.,]\d+)?)", _normalize(text))
    if not match:
        return None
    try:
        return float(match.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _to_int(text: str) -> Optional[int]:
    value = _to_number(text)
    if value is None:
        return None
    return int(round(value))


def _extract_listing_id(url: str) -> str:
    match = re.search(r"-id-(\d+)", url)
    return match.group(1) if match else ""


def _extract_type_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if "/venda/apartamentos/" in path or "venda-apartamento-" in path or "-apartamento-" in path:
        return "apartamento"
    if "/venda/casas/" in path or "venda-casa-" in path or "-casa-" in path:
        return "casa"
    return ""


def _build_search_url(property_type: str, page_number: int) -> str:
    base = SEARCH_URLS[property_type]
    if page_number <= 1:
        return base
    return f"{base}?pagina={page_number}"


def _extract_bairro_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    slug = path.rsplit("/", 1)[-1]
    slug = re.sub(r"-id-\d+.*$", "", slug)
    if "-fortaleza-ce-" not in slug:
        return ""
    prefix = slug.split("-fortaleza-ce-", 1)[0]
    tokens = [t for t in prefix.split("-") if t]
    if len(tokens) < 2:
        return ""

    generic = {
        "venda",
        "aluguel",
        "apartamento",
        "apartamentos",
        "casa",
        "casas",
        "com",
        "de",
        "do",
        "da",
        "das",
        "dos",
        "e",
        "na",
        "no",
        "nos",
        "nas",
        "quartos",
        "quarto",
        "banheiros",
        "banheiro",
        "vagas",
        "vaga",
        "suite",
        "suites",
        "piscina",
        "varanda",
        "gourmet",
        "m2",
        "m",
    }

    while tokens and tokens[-1] in generic:
        tokens.pop()
    while tokens and tokens[-1].isdigit():
        tokens.pop()
    if not tokens:
        return ""

    tail = tokens[-4:]
    while tail and tail[0] in generic:
        tail = tail[1:]
    while tail and tail[-1] in generic:
        tail = tail[:-1]
    return " ".join(tail).strip(" -")


def _first_json_ld_dict(page) -> dict:
    try:
        raw_scripts = page.locator('script[type="application/ld+json"]').all_text_contents()
    except Exception:
        raw_scripts = []

    best_item = {}
    for raw in raw_scripts:
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        if isinstance(parsed, dict):
            score = 0
            if parsed.get("offers"):
                score += 2
            if parsed.get("image"):
                score += 2
            if parsed.get("sku"):
                score += 1
            if parsed.get("name") and "zap imoveis" not in str(parsed.get("name", "")).lower():
                score += 2
            if parsed.get("description"):
                score += 1
            if score > 0 and score >= best_item.get("_score", 0):
                best_item = dict(parsed)
                best_item["_score"] = score
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    score = 0
                    if item.get("offers"):
                        score += 2
                    if item.get("image"):
                        score += 2
                    if item.get("sku"):
                        score += 1
                    if item.get("name") and "zap imoveis" not in str(item.get("name", "")).lower():
                        score += 2
                    if item.get("description"):
                        score += 1
                    if score > 0 and score >= best_item.get("_score", 0):
                        best_item = dict(item)
                        best_item["_score"] = score
    if "_score" in best_item:
        best_item.pop("_score", None)
    return best_item


def _json_ld_value(item: dict, key: str) -> str:
    value = item.get(key, "")
    if isinstance(value, dict):
        return str(value.get("value", ""))
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str):
                return entry
    return str(value) if value is not None else ""


def _json_ld_address(item: dict) -> dict:
    address = item.get("address")
    return address if isinstance(address, dict) else {}


def _json_ld_geo(item: dict) -> dict:
    geo = item.get("geo")
    return geo if isinstance(geo, dict) else {}


def _json_ld_offers(item: dict) -> dict:
    offers = item.get("offers")
    if isinstance(offers, dict):
        return offers
    if isinstance(offers, list) and offers and isinstance(offers[0], dict):
        return offers[0]
    return {}


def _extract_meta(page, selector: str) -> str:
    try:
        value = page.locator(selector).first.get_attribute("content") or ""
        return _clean_text(value)
    except Exception:
        return ""


def _extract_title(page, fallback: str) -> str:
    try:
        h1 = page.locator("h1").first.inner_text(timeout=5000)
        if h1:
            return _clean_text(h1)
    except Exception:
        pass
    title = page.title()
    if title:
        return _clean_text(title)
    title = _extract_meta(page, 'meta[property="og:title"]')
    if title and title.lower() != "zap imoveis":
        return title
    return fallback


def _extract_bairro_from_page(page) -> str:
    page_title = ""
    try:
        page_title = page.title()
    except Exception:
        page_title = ""

    patterns = [
        r"\bem\s+(.+?)\s*-\s*Fortaleza\b",
        r"\bde\s+(.+?)\s*-\s*Fortaleza\b",
    ]
    for source in [page_title, _extract_meta(page, 'meta[name="description"]')]:
        for pattern in patterns:
            match = re.search(pattern, source, flags=re.I)
            if match:
                return _clean_text(match.group(1))
    return ""


def _extract_image(page) -> str:
    image = _extract_meta(page, 'meta[property="og:image"]')
    if image:
        if image.startswith("//"):
            return f"https:{image}"
        if image.startswith("/"):
            return urljoin(BASE_URL, image)
        return image
    try:
        src = page.locator("img").first.get_attribute("src") or ""
        if src.startswith("//"):
            return f"https:{src}"
        if src.startswith("/"):
            return urljoin(BASE_URL, src)
        return src
    except Exception:
        return ""


def _is_blocked_content(text: str) -> bool:
    normalized = _normalize(text)
    return any(
        phrase in normalized
        for phrase in [
            "sorry, you have been blocked",
            "access denied",
            "unusual traffic",
            "blocked",
        ]
    )


def _page_looks_blocked(page) -> bool:
    try:
        title = page.title()
    except Exception:
        title = ""
    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception:
        body = ""
    try:
        html_text = page.content()
    except Exception:
        html_text = ""
    return _is_blocked_content(f"{title}\n{body}\n{html_text}")


def _goto_with_block_retries(page, url: str, *, attempts: int = 3, timeout_ms: int = 20000) -> bool:
    for attempt in range(1, attempts + 1):
        try:
            page.goto(url, wait_until="commit", timeout=timeout_ms)
            page.wait_for_timeout(700)
        except Exception as exc:
            print(f"[zap] falha ao abrir {url} tentativa {attempt}/{attempts}: {exc}", file=sys.stderr)
            if attempt < attempts:
                page.wait_for_timeout(1500 * attempt)
            continue

        if _page_looks_blocked(page):
            print(f"[zap] pagina bloqueada em {url} tentativa {attempt}/{attempts}; recarregando.", file=sys.stderr)
            try:
                page.reload(wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception:
                pass
            page.wait_for_timeout(1500 * attempt)
            if _page_looks_blocked(page):
                if attempt < attempts:
                    continue
                return False
        return True
    return False


def _extract_price(text: str) -> str:
    match = re.search(r"R\$\s*[\d\.\,]+", text)
    return match.group(0).replace("R$ ", "R$").strip() if match else ""


def _extract_area(text: str) -> Optional[float]:
    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*m²",
        r"(\d+(?:[.,]\d+)?)\s*m2",
        r"(\d+(?:[.,]\d+)?)\s+metros?\s+quadrados?",
    ]
    for pattern in patterns:
        match = re.search(pattern, _normalize(text), flags=re.I | re.S)
        if match:
            return _to_number(match.group(1))
    return None


def _extract_rooms(text: str) -> Optional[int]:
    patterns = [r"(\d+)\s+quartos?", r"(\d+)\s+dormitorios?", r"(\d+)\s+dormit[óo]rios?"]
    for pattern in patterns:
        match = re.search(pattern, _normalize(text), flags=re.I)
        if match:
            return int(match.group(1))
    return None


def _extract_bathrooms(text: str) -> Optional[int]:
    match = re.search(r"(\d+)\s+banheiros?", _normalize(text), flags=re.I)
    return int(match.group(1)) if match else None


def _extract_parking(text: str) -> Optional[int]:
    patterns = [r"(\d+)\s+vagas?\s+de\s+garagem", r"(\d+)\s+vagas?"]
    for pattern in patterns:
        match = re.search(pattern, _normalize(text), flags=re.I)
        if match:
            return int(match.group(1))
    return None


def _extract_suite_count(text: str) -> Optional[int]:
    match = re.search(r"(\d+)\s+su[ii]tes?", _normalize(text), flags=re.I)
    return int(match.group(1)) if match else None


def _extract_floor(text: str) -> str:
    match = re.search(r"(\d+)\s*(?:º|o)?\s*andar", _normalize(text), flags=re.I)
    if match:
        return match.group(1)
    match = re.search(r"andar\s*(\d+)", _normalize(text), flags=re.I)
    return match.group(1) if match else ""


def _extract_feature_flags(text: str) -> dict[str, str]:
    normalized = _normalize(text)
    return {
        "tem_portaria_24h": str(int(any(term in normalized for term in ["portaria 24", "portaria eletronica", "portaria"]))),
        "tem_vista_pro_mar": str(int(any(term in normalized for term in ["vista para o mar", "vista mar", "frente mar", "beira mar"]))),
        "tem_condominio_fechado": str(int("condominio fechado" in normalized)),
        "tem_piscina": str(int("piscina" in normalized)),
        "tem_deck": str(int("deck" in normalized)),
        "tem_varanda": str(int("varanda" in normalized)),
        "tem_academia": str(int(any(term in normalized for term in ["academia", "fitness"]))),
        "tem_salao_festas": str(int(any(term in normalized for term in ["salao de festa", "salao de festas"]))),
        "tem_salao_jogos": str(int("salao de jogos" in normalized)),
        "tem_quadra_campo": str(int(any(term in normalized for term in ["quadra", "campo de futebol", "campo society", "quadra poliesportiva"]))),
    }


def _extract_text_field(page, fallback: str = "") -> str:
    value = _extract_meta(page, 'meta[name="description"]')
    return value or fallback


def _extract_structured_data(page) -> dict:
    item = _first_json_ld_dict(page)
    address = _json_ld_address(item)
    geo = _json_ld_geo(item)
    offers = _json_ld_offers(item)

    price = ""
    raw_price = offers.get("price") or offers.get("lowPrice") or ""
    if raw_price:
        price = f"R$ {raw_price}" if not str(raw_price).startswith("R$") else str(raw_price)

    return {
        "titulo": _extract_title(page, str(item.get("name", ""))),
        "descricao": _extract_meta(page, 'meta[name="description"]') or str(item.get("description", "")),
        "image": (
            (item.get("image")[0] if isinstance(item.get("image"), list) and item.get("image") else "")
            or (str(item.get("image", "")) if isinstance(item.get("image"), str) else "")
            or _extract_image(page)
        ),
        "street": str(address.get("streetAddress", "")),
        "neighborhood": str(address.get("addressLocality", "")),
        "region": str(address.get("addressRegion", "")),
        "latitude": str(geo.get("latitude", "")),
        "longitude": str(geo.get("longitude", "")),
        "price": price,
        "floor_size": _json_ld_value(item, "floorSize"),
        "rooms": _json_ld_value(item, "numberOfRooms"),
        "bathrooms": _json_ld_value(item, "numberOfBathroomsTotal"),
        "suites": _json_ld_value(item, "numberOfSuites"),
        "floor": _json_ld_value(item, "floorLevel"),
        "parking": _json_ld_value(item, "numberOfParkingSpaces"),
        "date_posted": str(item.get("datePosted", "")),
        "seller": str(item.get("publisher", {}).get("name", "")) if isinstance(item.get("publisher"), dict) else "",
    }


@dataclass
class ListingRecord:
    listing_id: str = ""
    titulo: str = ""
    apartamento_ou_casa: str = ""
    tipo_imovel: str = ""
    estado: str = "CE"
    cidade: str = "Fortaleza"
    bairro: str = ""
    rua: str = ""
    numero: str = ""
    endereco: str = ""
    metragem: Optional[float] = None
    quartos: Optional[int] = None
    banheiros: Optional[int] = None
    suites: Optional[int] = None
    andar: str = ""
    estacionamentos: Optional[int] = None
    preco_anuncio: str = ""
    latitude: str = ""
    longitude: str = ""
    tem_portaria_24h: str = "0"
    tem_vista_pro_mar: str = "0"
    tem_condominio_fechado: str = "0"
    tem_piscina: str = "0"
    tem_deck: str = "0"
    tem_varanda: str = "0"
    tem_academia: str = "0"
    tem_salao_festas: str = "0"
    tem_salao_jogos: str = "0"
    tem_quadra_campo: str = "0"
    descricao: str = ""
    anuncio_criado: str = ""
    corretora: str = ""
    nota_media: str = ""
    url: str = ""
    imagem_url: str = ""

    def as_dict(self) -> dict[str, str]:
        def fmt(value):
            if value is None:
                return ""
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value)

        return {
            "listing_id": self.listing_id,
            "titulo": self.titulo,
            "apartamento_ou_casa": self.apartamento_ou_casa,
            "tipo_imovel": self.tipo_imovel,
            "estado": self.estado,
            "cidade": self.cidade,
            "bairro": self.bairro,
            "rua": self.rua,
            "numero": self.numero,
            "endereco": self.endereco,
            "metragem": fmt(self.metragem),
            "quartos": fmt(self.quartos),
            "banheiros": fmt(self.banheiros),
            "suites": fmt(self.suites),
            "andar": self.andar,
            "estacionamentos": fmt(self.estacionamentos),
            "preco_anuncio": self.preco_anuncio,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "tem_portaria_24h": self.tem_portaria_24h,
            "tem_vista_pro_mar": self.tem_vista_pro_mar,
            "tem_condominio_fechado": self.tem_condominio_fechado,
            "tem_piscina": self.tem_piscina,
            "tem_deck": self.tem_deck,
            "tem_varanda": self.tem_varanda,
            "tem_academia": self.tem_academia,
            "tem_salao_festas": self.tem_salao_festas,
            "tem_salao_jogos": self.tem_salao_jogos,
            "tem_quadra_campo": self.tem_quadra_campo,
            "descricao": self.descricao,
            "anuncio_criado": self.anuncio_criado,
            "corretora": self.corretora,
            "nota_media": self.nota_media,
            "url": self.url,
            "imagem_url": self.imagem_url,
        }


def _collect_listing_urls(page, property_type: str, page_number: int) -> list[str]:
    if not _goto_with_block_retries(page, _build_search_url(property_type, page_number), attempts=3, timeout_ms=30000):
        print(f"[zap] busca bloqueada ou inacessivel para {property_type} pagina {page_number}", file=sys.stderr)
        return []

    page.wait_for_timeout(500)
    try:
        hrefs = page.locator('a[href*="/imovel/"]').evaluate_all("els => els.map(el => el.href).filter(Boolean)")
    except Exception:
        hrefs = []

    urls: list[str] = []
    for href in hrefs:
        if "/imovel/" not in href:
            continue
        if _extract_type_from_url(href) != property_type:
            continue
        if href not in urls:
            urls.append(href)

    return urls


def _scrape_detail(page, url: str) -> ListingRecord:
    if not _goto_with_block_retries(page, url, attempts=4, timeout_ms=20000):
        raise RuntimeError(f"pagina bloqueada apos retries: {url}")

    page.wait_for_timeout(500)
    try:
        body_text = _clean_text(page.locator("body").inner_text(timeout=7000))
    except Exception:
        body_text = ""
    try:
        html_text = page.content()
    except Exception:
        html_text = ""
    combined_text = f"{body_text}\n{html_text}"
    structured = _extract_structured_data(page)

    record = ListingRecord()
    record.listing_id = _extract_listing_id(url)
    record.titulo = structured.get("titulo", "") or _extract_title(page, body_text)
    record.url = url
    record.apartamento_ou_casa = _extract_type_from_url(url)
    record.tipo_imovel = record.apartamento_ou_casa
    record.bairro = _extract_bairro_from_page(page) or structured.get("neighborhood", "") or _extract_bairro_from_url(url)
    record.rua = structured.get("street", "")
    record.numero = re.search(r"\b(\d{1,6})\b", record.rua).group(1) if re.search(r"\b(\d{1,6})\b", record.rua) else ""
    if not record.rua:
        match = re.search(r"(rua|avenida|av\.|travessa|alameda|rodovia|estrada)\s+[^,\n]+", body_text, flags=re.I)
        if match:
            record.rua = _clean_text(match.group(0))
            record.numero = re.search(r"\b(\d{1,6})\b", record.rua).group(1) if re.search(r"\b(\d{1,6})\b", record.rua) else ""

    record.endereco = ", ".join([part for part in [record.rua, record.bairro, "Fortaleza - CE"] if part])
    record.metragem = _to_number(structured.get("floor_size", "")) or _extract_area(combined_text)
    record.quartos = _to_int(structured.get("rooms", "")) or _extract_rooms(combined_text)
    record.banheiros = _to_int(structured.get("bathrooms", "")) or _extract_bathrooms(combined_text)
    record.suites = _to_int(structured.get("suites", "")) or _extract_suite_count(combined_text)
    record.andar = structured.get("floor", "") or _extract_floor(combined_text)
    record.estacionamentos = _to_int(structured.get("parking", "")) or _extract_parking(combined_text)
    record.preco_anuncio = structured.get("price", "") or _extract_price(combined_text)
    record.latitude = structured.get("latitude", "")
    record.longitude = structured.get("longitude", "")
    if not record.latitude or not record.longitude:
        lat = re.search(r'"latitude"\s*:\s*(-?\d+(?:\.\d+)?)', html_text, flags=re.I | re.S)
        lon = re.search(r'"longitude"\s*:\s*(-?\d+(?:\.\d+)?)', html_text, flags=re.I | re.S)
        if lat and lon:
            record.latitude, record.longitude = lat.group(1), lon.group(1)

    record.descricao = structured.get("descricao", "") or _extract_meta(page, 'meta[name="description"]')
    record.anuncio_criado = structured.get("date_posted", "")
    record.corretora = structured.get("seller", "")
    record.nota_media = ""
    record.imagem_url = structured.get("image", "")
    if not record.imagem_url:
        record.imagem_url = _extract_image(page)

    record.__dict__.update(_extract_feature_flags(combined_text))
    return record


def _append_row(output_path: Path, row: dict[str, str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0
    with output_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _load_seen_urls(output_path: Path) -> set[str]:
    seen_urls: set[str] = set()
    if not output_path.exists() or output_path.stat().st_size == 0:
        return seen_urls
    try:
        with output_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = (row or {}).get("url", "").strip()
                if url:
                    seen_urls.add(url)
    except Exception as exc:
        print(f"[zap] nao foi possivel ler o CSV existente para retomar: {exc}", file=sys.stderr)
    return seen_urls


def scrape_zap(output_path: Path, max_listings_per_type: int = 5000, headless: bool = True) -> list[dict[str, str]]:
    _ensure_playwright()
    from playwright.sync_api import sync_playwright

    rows: list[dict[str, str]] = []
    seen_urls: set[str] = _load_seen_urls(output_path)
    if seen_urls:
        print(f"[zap] retomando com {len(seen_urls)} URLs ja salvas em {output_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(
            viewport={"width": 1440, "height": 2200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        detail_page = browser.new_page(
            viewport={"width": 1440, "height": 2200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        try:
            for property_type in ("apartamento", "casa"):
                print(f"[zap] coletando URLs de {property_type}s...")
                page_number = 1
                empty_pages = 0
                collected_this_type = 0

                while True:
                    if max_listings_per_type and collected_this_type >= max_listings_per_type:
                        break

                    urls = _collect_listing_urls(page, property_type=property_type, page_number=page_number)
                    new_urls = [url for url in urls if url not in seen_urls]
                    if not urls or not new_urls:
                        empty_pages += 1
                    else:
                        empty_pages = 0

                    if empty_pages >= 3:
                        print(f"[zap] sem novas URLs em {property_type} na pagina {page_number}, encerrando tipo.")
                        break

                    if not new_urls:
                        print(f"[zap] pagina {page_number} sem URLs novas para {property_type}")
                        page_number += 1
                        continue

                    print(f"[zap] pagina {page_number}: {len(new_urls)} novas URLs de {property_type}")
                    for index, url in enumerate(new_urls, start=1):
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        try:
                            record = _scrape_detail(detail_page, url)
                            row = record.as_dict()
                            rows.append(row)
                            _append_row(output_path, row)
                            collected_this_type += 1
                            print(f"[zap] {property_type} p{page_number} {index}/{len(new_urls)} OK: {record.bairro or record.rua or url}")
                            if max_listings_per_type and collected_this_type >= max_listings_per_type:
                                break
                        except Exception as exc:
                            print(f"[zap] erro ao ler {url}: {exc}", file=sys.stderr)

                    page_number += 1
        finally:
            detail_page.close()
            page.close()
            browser.close()

    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scraper do ZAP Imoveis para venda de apartamentos e casas em Fortaleza.")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent / "outputs" / "zap_venda_fortaleza.csv"),
        help="Caminho do CSV de saida.",
    )
    parser.add_argument(
        "--max-listings-per-type",
        type=int,
        default=5000,
        help="Limite maximo por tipo de imovel.",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Executa o navegador em modo headless.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    output_path = Path(args.output)
    rows = scrape_zap(output_path=output_path, max_listings_per_type=args.max_listings_per_type, headless=args.headless)
    print(f"[zap] finalizado com {len(rows)} registros em {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
