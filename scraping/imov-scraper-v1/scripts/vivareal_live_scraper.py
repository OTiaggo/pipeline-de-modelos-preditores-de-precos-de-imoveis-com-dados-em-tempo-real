import argparse
import csv
import html
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from imov_scraper.core import (  # noqa: E402
    BAIRROS_FORTALEZA,
    _clean_description,
    _extract_features,
)


FIELDS = [
    "listing_id", "titulo", "apartamento_ou_casa", "tipo_imovel", "estado",
    "cidade", "bairro", "rua", "numero", "endereco", "metragem", "quartos",
    "banheiros", "suites", "andar", "estacionamentos", "preco_anuncio",
    "latitude", "longitude", "tem_portaria_24h", "tem_vista_pro_mar",
    "tem_condominio_fechado", "tem_piscina", "tem_deck",
    "tem_varanda", "tem_academia",
    "tem_salao_festas", "tem_salao_jogos", "tem_quadra_campo", "descricao",
    "anuncio_criado", "corretora", "nota_media", "url", "imagem_url",
]

VIVAREAL = "https://www.vivareal.com.br"
BASE_URLS = [
    ("geral", f"{VIVAREAL}/venda/ceara/fortaleza/"),
    ("apartamentos", f"{VIVAREAL}/venda/ceara/fortaleza/apartamento_residencial/"),
    ("casas", f"{VIVAREAL}/venda/ceara/fortaleza/casa_residencial/"),
]
VIVAREAL_NEIGHBORHOOD_SLUGS = [
    "aldeota",
    "benfica",
    "cambeba",
    "centro",
    "cid-dos-funcionarios",
    "coco",
    "edson-queiroz",
    "engenheiro-luciano-cavalcante",
    "farias-brito",
    "meireles",
    "messejana",
    "mondubim",
    "papicu",
    "parangaba",
    "passare",
    "planalto-ayrton-senna",
    "prefeito-jose-walter",
    "siqueira",
    "varjota",
]
TYPE_LABELS = {
    "APARTMENT": "apartamento",
    "APARTMENT_UNIT": "apartamento",
    "PENTHOUSE": "apartamento",
    "KITNET": "apartamento",
    "STUDIO": "apartamento",
    "FLAT": "apartamento",
    "HOUSE": "casa",
    "HOME": "casa",
    "TWO_STORY_HOUSE": "casa",
    "CONDOMINIUM": "casa",
    "VILLAGE_HOUSE": "casa",
    "Apartment": "apartamento",
    "House": "casa",
}


def fetch(url: str) -> str:
    cmd = [
        "curl.exe",
        "-f",
        "-L",
        url,
        "-H",
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "-H",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H",
        "Accept-Language: pt-BR,pt;q=0.9,en;q=0.8",
        "--compressed",
        "--max-time",
        "45",
        "-sS",
    ]
    return subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("/", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def known_neighborhood_slugs() -> set[str]:
    slugs = {slugify(bairro) for bairro in BAIRROS_FORTALEZA}
    slugs.update(VIVAREAL_NEIGHBORHOOD_SLUGS)
    slugs.discard("")
    return slugs


KNOWN_NEIGHBORHOOD_SLUGS = known_neighborhood_slugs()


def int_cell(value):
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        value = value[0] if value else ""
    try:
        return int(float(str(value).replace(",", ".")))
    except Exception:
        m = re.search(r"\d+", str(value))
        return int(m.group(0)) if m else ""


def number_cell(value):
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        value = value[0] if value else ""
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        m = re.search(r"\d+(?:[.,]\d+)?", str(value))
        return float(m.group(0).replace(",", ".")) if m else ""


def bool_cell(value) -> int:
    return int(bool(value))


def first_list_value(value):
    if isinstance(value, list):
        return value[0] if value else ""
    return value if value is not None else ""


def dict_or_empty(value) -> dict:
    return value if isinstance(value, dict) else {}


def parse_jsonld_items(html_text: str) -> dict:
    items = {}
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S):
        try:
            data = json.loads(html.unescape(m.group(1)))
        except Exception:
            continue
        if data.get("@type") != "ItemList":
            continue
        for entry in data.get("itemListElement") or []:
            item = entry.get("item") or {}
            listing_id = str(item.get("@id") or "")
            if listing_id:
                items[listing_id] = item
    return items


def parse_next_content(html_text: str) -> dict:
    chunks = []
    for m in re.finditer(r"<script[^>]*>self\.__next_f\.push\((.*?)\)</script>", html_text, re.S):
        try:
            payload = json.loads(m.group(1))
        except Exception:
            continue
        if len(payload) > 1 and isinstance(payload[1], str):
            chunks.append(payload[1])
    stream = "".join(chunks)
    marker = '"content":{"listings"'
    idx = stream.find(marker)
    if idx < 0:
        return {}
    start = stream.find("{", idx + len('"content":') - 1)
    if start < 0:
        return {}

    level = 0
    in_string = False
    escaped = False
    end = None
    for pos, ch in enumerate(stream[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                level += 1
            elif ch == "}":
                level -= 1
                if level == 0:
                    end = pos + 1
                    break
    if end is None:
        return {}
    try:
        return json.loads(stream[start:end])
    except Exception:
        return {}


def has_neighborhood_conflict(value: str, bairro: str) -> bool:
    if not value or not bairro:
        return False
    haystack = slugify(value)
    current = slugify(bairro)
    if not haystack or not current:
        return False
    if current in haystack:
        return False
    return any(slug in haystack for slug in KNOWN_NEIGHBORHOOD_SLUGS if slug != current)


def description_mentions_other_neighborhood(description: str, bairro: str) -> bool:
    if not description or not bairro:
        return False
    current = slugify(bairro)
    for m in re.finditer(r"\bbairro\s+([A-Za-zÀ-ÿ0-9\s/-]{2,60})", description, re.I):
        mentioned = slugify(m.group(1))
        if mentioned and current not in mentioned:
            if any(slug in mentioned for slug in KNOWN_NEIGHBORHOOD_SLUGS if slug != current):
                return True
    return False


def ld_matches_listing(listing: dict, ld_item: dict) -> bool:
    if not ld_item:
        return False
    address = dict_or_empty(listing.get("address"))
    ld_address = dict_or_empty(ld_item.get("address"))
    city = (address.get("city") or "").strip().lower()
    ld_city = (ld_address.get("addressLocality") or "").strip().lower()
    state = (address.get("stateAcronym") or "").strip().upper()
    ld_state = (ld_address.get("addressRegion") or "").strip().upper()
    if city and ld_city and city != ld_city:
        return False
    if state and ld_state and state != ld_state:
        return False
    bairro = address.get("neighborhood") or ""
    probe = " ".join([
        ld_item.get("url") or "",
        ld_item.get("name") or "",
        ld_item.get("keywords") or "",
        ld_item.get("description") or "",
    ])
    return not has_neighborhood_conflict(probe, bairro)


def clean_literal(value) -> str:
    value = "" if value is None else str(value).strip()
    if not value or value.startswith("$") or value.lower() in {"undefined", "null", "none"}:
        return ""
    return value


def amenity_text(ld_item: dict, listing: dict) -> str:
    values = []
    values.extend(str(v) for v in ((listing.get("amenities") or {}).get("values") or []))
    for feature in ld_item.get("amenityFeature") or []:
        if isinstance(feature, dict):
            values.append(str(feature.get("value") or ""))
            values.append(str(feature.get("name") or ""))
    aliases = {
        "Concierge 24h": "portaria 24h",
        "Reception": "portaria",
        "Watchman": "porteiro",
        "Gated Community": "condominio fechado",
        "Pool": "piscina",
        "Adult Pool": "piscina",
        "Childrens Pool": "piscina",
        "Deck": "deck",
        "Gourmet Balcony": "varanda",
        "Balcony": "varanda",
        "Gym": "academia",
        "Party Hall": "salao de festas",
        "Games Room": "salao de jogos",
        "Sports Court": "quadra",
        "Football Field": "campo de futebol",
        "Panoramic View": "vista",
        "Sea View": "vista mar",
        "Ocean View": "vista mar",
    }
    translated = [aliases.get(v, v) for v in values]
    return " ".join([*values, *translated])


def listing_kind(listing: dict, ld_item: dict, text: str) -> str:
    unit_type = listing.get("unitType") or ld_item.get("@type") or ""
    if unit_type in TYPE_LABELS:
        return TYPE_LABELS[unit_type]
    low = text.lower()
    if "apartamento" in low or "apto" in low or "studio" in low or "flat" in low:
        return "apartamento"
    if "casa" in low or "sobrado" in low:
        return "casa"
    return ""


def image_url(listing: dict, ld_item: dict) -> str:
    images = ld_item.get("image") or []
    if images:
        return images[0]
    media_images = ((listing.get("medias") or {}).get("images") or [])
    if not media_images:
        return ""
    src = media_images[0].get("dangerousSrc") or ""
    alt = media_images[0].get("alt") or listing.get("title") or ""
    desc = slugify(alt) or "imovel"
    return src.replace("{description}", desc).replace("{action}", "fit-in").replace("{width}", "614").replace("{height}", "297")


def listing_url(listing: dict, ld_item: dict, bairro: str) -> str:
    candidates = [listing.get("href") or "", ld_item.get("url") or ""]
    for candidate in candidates:
        if not candidate:
            continue
        url = urljoin(VIVAREAL, candidate)
        if not has_neighborhood_conflict(url, bairro):
            return url
    return ""


def advertiser_name(listing: dict) -> str:
    advertiser = listing.get("advertiser") or {}
    if isinstance(advertiser, dict):
        return advertiser.get("name") or ""
    return ""


def advertiser_rating(listing: dict) -> str:
    advertiser = listing.get("advertiser") or {}
    if isinstance(advertiser, dict):
        rating = advertiser.get("rating")
        if isinstance(rating, dict):
            rating = rating.get("average") or rating.get("value")
        return rating if rating not in (None, "") else ""
    return ""


def listing_date(listing: dict) -> str:
    for key in ("createdAt", "createdDate", "publicationDate", "publishedAt", "updatedAt"):
        value = listing.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def parking_spaces(amenities: dict, text: str):
    direct = first_list_value(amenities.get("parkingSpaces"))
    if direct not in (None, ""):
        return direct
    m = re.search(r"(\d+)\s+vagas?", text, re.I)
    return m.group(1) if m else ""


def floor_value(amenities: dict, features: dict):
    value = amenities.get("unitFloor") if amenities.get("unitFloor") is not None else features.get("andar")
    value = int_cell(value)
    if value == "":
        return ""
    return value if 0 <= int(value) <= 80 else ""


def normalize_row(listing: dict, ld_item: dict) -> dict:
    if not ld_matches_listing(listing, ld_item):
        ld_item = {}
    listing_id = str(listing.get("id") or ld_item.get("@id") or "")
    title = listing.get("title") or ld_item.get("name") or ""
    description_raw = ld_item.get("description") or listing.get("description") or ""
    description = _clean_description(description_raw)
    text = " ".join([
        title,
        ld_item.get("keywords") or "",
        description_raw,
        amenity_text(ld_item, listing),
    ])
    kind = listing_kind(listing, ld_item, text)

    address = dict_or_empty(listing.get("address"))
    ld_address = dict_or_empty(ld_item.get("address"))
    amenities = dict_or_empty(listing.get("amenities"))
    coordinates = dict_or_empty(address.get("coordinates"))
    sale = dict_or_empty(dict_or_empty(listing.get("prices")).get("sale"))
    offers = dict_or_empty(ld_item.get("offers"))
    floor_size = dict_or_empty(ld_item.get("floorSize"))
    features = _extract_features(text)

    street = clean_literal(address.get("street") or ld_address.get("streetAddress") or "")
    number = clean_literal(address.get("streetNumber") or "")
    bairro = address.get("neighborhood") or ""
    city = address.get("city") or ld_address.get("addressLocality") or ""
    state = address.get("stateAcronym") or ld_address.get("addressRegion") or ""
    endereco = ", ".join(part for part in [street, number] if part)
    endereco = " - ".join(part for part in [endereco, bairro] if part)
    city_state = " / ".join(part for part in [city, state] if part)
    endereco = ", ".join(part for part in [endereco, city_state] if part)
    if description_mentions_other_neighborhood(description_raw, bairro):
        description_raw = ""
        description = ""

    return {
        "listing_id": listing_id,
        "titulo": title,
        "apartamento_ou_casa": kind,
        "tipo_imovel": listing.get("unitType") or ld_item.get("@type") or kind,
        "estado": state,
        "cidade": city,
        "bairro": bairro,
        "rua": street,
        "numero": number,
        "endereco": endereco,
        "metragem": int_cell(first_list_value(amenities.get("usableAreas")) or floor_size.get("value")),
        "quartos": int_cell(first_list_value(amenities.get("bedrooms")) or ld_item.get("numberOfBedrooms") or ld_item.get("numberOfRooms")),
        "banheiros": int_cell(first_list_value(amenities.get("bathrooms")) or ld_item.get("numberOfBathroomsTotal")),
        "suites": int_cell(first_list_value(amenities.get("suites")) or features.get("suites")),
        "andar": floor_value(amenities, features),
        "estacionamentos": int_cell(parking_spaces(amenities, text)),
        "preco_anuncio": number_cell(sale.get("value") or offers.get("price")),
        "latitude": number_cell(coordinates.get("latitude")),
        "longitude": number_cell(coordinates.get("longitude")),
        "tem_portaria_24h": bool_cell(features.get("portaria")),
        "tem_vista_pro_mar": bool_cell(features.get("vista_mar")),
        "tem_condominio_fechado": bool_cell(features.get("condominio_fechado")),
        "tem_piscina": bool_cell(features.get("piscina")),
        "tem_deck": bool_cell(features.get("deck")),
        "tem_varanda": bool_cell(features.get("varanda")),
        "tem_academia": bool_cell(features.get("academia")),
        "tem_salao_festas": bool_cell(features.get("salao_festa")),
        "tem_salao_jogos": bool_cell(features.get("salao_jogos")),
        "tem_quadra_campo": bool_cell(features.get("quadra_campo")),
        "descricao": description,
        "anuncio_criado": listing_date(listing),
        "corretora": advertiser_name(listing),
        "nota_media": advertiser_rating(listing),
        "url": listing_url(listing, ld_item, bairro),
        "imagem_url": image_url(listing, ld_item),
    }


def rows_from_html(html_text: str) -> list[dict]:
    ld_items = parse_jsonld_items(html_text)
    content = parse_next_content(html_text)
    rows = []
    for listing in content.get("listings") or []:
        listing_id = str(listing.get("id") or "")
        rows.append(normalize_row(listing, ld_items.get(listing_id) or {}))
    if rows:
        return rows
    for listing_id, item in ld_items.items():
        listing = {"id": listing_id, "business": "SALE"}
        rows.append(normalize_row(listing, item))
    return rows


def page_url(base_url: str, page: int) -> str:
    return base_url if page == 1 else f"{base_url}?pagina={page}"


def query_urls() -> list[tuple[str, str, int]]:
    urls = [(label, url, 80) for label, url in BASE_URLS]
    seen_slugs = set()
    for slug in VIVAREAL_NEIGHBORHOOD_SLUGS:
        seen_slugs.add(slug)
        urls.append((f"bairro:{slug}", f"{VIVAREAL}/venda/ceara/fortaleza/bairros/{slug}/", 35))
    for bairro in sorted(BAIRROS_FORTALEZA):
        slug = slugify(bairro)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        urls.append((f"bairro:{bairro}", f"{VIVAREAL}/venda/ceara/fortaleza/bairros/{slug}/", 25))
    return urls


def valid_row(row: dict) -> bool:
    if row["apartamento_ou_casa"] not in {"apartamento", "casa"}:
        return False
    if str(row["cidade"]).strip().lower() != "fortaleza":
        return False
    if str(row["estado"]).strip().upper() != "CE":
        return False
    return bool(row["listing_id"] and row["preco_anuncio"])


def collect(limit: int, delay: float):
    rows = []
    seen = set()
    for label, base_url, max_pages in query_urls():
        empty_streak = 0
        for page in range(1, max_pages + 1):
            if len(rows) >= limit:
                return rows
            url = page_url(base_url, page)
            print(f"[VIVAREAL] {label} p{page}: {len(rows)}/{limit}", flush=True)
            try:
                html_text = fetch(url)
            except Exception as exc:
                print(f"[VIVAREAL] parada em {label} p{page}: {exc}", flush=True)
                break
            added = 0
            parsed = rows_from_html(html_text)
            if not parsed:
                break
            for row in parsed:
                if not valid_row(row) or row["listing_id"] in seen:
                    continue
                seen.add(row["listing_id"])
                rows.append(row)
                added += 1
                if len(rows) >= limit:
                    return rows
            print(f"[VIVAREAL] {label} p{page}: {added} novos", flush=True)
            if added == 0:
                empty_streak += 1
                if empty_streak >= 3:
                    break
            else:
                empty_streak = 0
            time.sleep(delay)
    return rows


def main():
    ap = argparse.ArgumentParser(description="Coleta VivaReal live para venda de apartamentos/casas em Fortaleza/CE.")
    ap.add_argument("--out", default=str(ROOT / "saida" / "vivareal_live_20k.csv"))
    ap.add_argument("--limit", type=int, default=20000)
    ap.add_argument("--delay", type=float, default=0.15)
    args = ap.parse_args()

    rows = collect(limit=args.limit, delay=args.delay)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"OK: {len(rows)} linhas salvas em {out.resolve()}")


if __name__ == "__main__":
    main()
