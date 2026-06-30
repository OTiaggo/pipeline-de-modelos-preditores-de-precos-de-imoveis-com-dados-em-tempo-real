from __future__ import annotations

import argparse
import csv
import json
import re
import random
import time
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests


BASE_URL = "https://www.vivareal.com.br"
HTML_DIR = Path(__file__).resolve().parent / "html_scraping"
OUTPUT_FILE = Path(__file__).resolve().parent / "outputs" / "vivareal_fortaleza.csv"
SEARCH_URL_TEMPLATES = [
    f"{BASE_URL}/venda/ceara/fortaleza/?pagina={{page}}",
    f"{BASE_URL}/venda/ceara/fortaleza/apartamento/?pagina={{page}}",
    f"{BASE_URL}/venda/ceara/fortaleza/casa/?pagina={{page}}",
]
REQUEST_TIMEOUT = 30
REQUEST_RETRIES = 6
DEFAULT_TARGET_RECORDS = 10_000
DEFAULT_MAX_PAGES = 500
DEFAULT_DELAY_SECONDS = 8.0
DEFAULT_DETAIL_DELAY_SECONDS = 1.5
DEFAULT_429_BACKOFF_SECONDS = 30.0


AMENITY_MAP = {
    "CONCIERGE_24H": "tem_portaria_24h",
    "SEA_VIEW": "tem_vista_pro_mar",
    "GATED_COMMUNITY": "tem_condominio_fechado",
    "POOL": "tem_piscina",
    "GOURMET_BALCONY": "tem_varanda",
    "BALCONY": "tem_varanda",
    "GYM": "tem_academia",
    "PARTY_HALL": "tem_salao_festas",
    "GAME_ROOM": "tem_salao_jogos",
    "MULTI_SPORT_COURT": "tem_quadra_campo",
    "SPORTS_COURT": "tem_quadra_campo",
    "COURT": "tem_quadra_campo",
    "BARBECUE_GRILL": "tem_deck",
    "DECK": "tem_deck",
}


def normalize_text(value: str) -> str:
    value = unescape(value or "")
    value = value.replace("\\u0026", "&").replace("\\u003e", ">")
    return re.sub(r"\s+", " ", value).strip()


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return normalize_text(value)


def extract_number(value: str, default: Optional[int] = None) -> Optional[int]:
    match = re.search(r"-?\d+", value or "")
    return int(match.group(0)) if match else default


def extract_float(value: str, default: Optional[float] = None) -> Optional[float]:
    match = re.search(r"-?\d+(?:\.\d+)?", value or "")
    return float(match.group(0)) if match else default


def read_html_files() -> List[Path]:
    if not HTML_DIR.exists():
        return []
    return sorted(HTML_DIR.glob("*.html"))


def find_listing_id(text: str) -> Optional[str]:
    match = re.search(r'"listingId":"?(\d+)"?', text)
    if match:
        return match.group(1)
    match = re.search(r'id-(\d+)', text)
    return match.group(1) if match else None


def find_first(pattern: str, text: str, flags: int = re.S) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1) if match else ""


def parse_search_card(inner_html: str, opening_tag: str) -> Dict[str, object]:
    href = find_first(r'href="([^"]+)"', opening_tag)
    title = normalize_text(find_first(r'title="([^"]+)"', opening_tag))
    listing_id = find_listing_id(href) or find_listing_id(title)

    area_text = find_first(
        r'data-cy="rp-cardProperty-propertyArea-txt"[^>]*>(.*?)</li>', inner_html
    )
    bedroom_text = find_first(
        r'data-cy="rp-cardProperty-bedroomQuantity-txt"[^>]*>(.*?)</li>', inner_html
    )
    bathroom_text = find_first(
        r'data-cy="rp-cardProperty-bathroomQuantity-txt"[^>]*>(.*?)</li>', inner_html
    )
    parking_text = find_first(
        r'data-cy="rp-cardProperty-parkingSpacesQuantity-txt"[^>]*>(.*?)</li>',
        inner_html,
    )
    location_text = find_first(
        r'data-cy="rp-cardProperty-location-txt"[^>]*>(.*?)</(?:h2|p)>', inner_html
    )
    street_text = find_first(
        r'data-cy="rp-cardProperty-street-txt"[^>]*>(.*?)</(?:p|span|h3)>', inner_html
    )
    price_text = find_first(
        r'data-cy="rp-cardProperty-price-txt"[^>]*>(.*?)</[^>]+>', inner_html
    )
    image_src = find_first(r'<img[^>]+src="([^"]+)"', inner_html)

    type_text = ""
    if title and " para " in title:
        type_text = title.split(" para ", 1)[0].strip()

    neighborhood = ""
    city = ""
    if location_text:
        location_text = strip_tags(location_text)
        if " em " in location_text:
            location_text = location_text.split(" em ", 1)[1]
        location_parts = [part.strip() for part in location_text.split(",") if part.strip()]
        if location_parts:
            neighborhood = location_parts[0]
        if len(location_parts) > 1:
            city = location_parts[1]

    return {
        "listing_id": listing_id,
        "titulo": title,
        "tipo_imovel": type_text,
        "apartamento_ou_casa": type_text,
        "metragem": extract_number(strip_tags(area_text)),
        "quartos": extract_number(strip_tags(bedroom_text)),
        "banheiros": extract_number(strip_tags(bathroom_text)),
        "estacionamentos": extract_number(strip_tags(parking_text)),
        "preco_anuncio": normalize_text(strip_tags(price_text)).replace("R$", "").strip(),
        "bairro": neighborhood,
        "cidade": city,
        "rua": normalize_text(strip_tags(street_text)),
        "url": urljoin(BASE_URL, href) if href else "",
        "imagem_url": image_src,
    }


def parse_card_page(text: str) -> List[Dict[str, object]]:
    pattern = re.compile(
        r'(<a\b[^>]*class="[^"]*\bgroup/card\b[^"]*"[^>]*>)(.*?)</a>',
        re.S,
    )
    records: List[Dict[str, object]] = []
    for opening_tag, inner_html in pattern.findall(text):
        record = parse_search_card(inner_html, opening_tag)
        if record.get("listing_id"):
            records.append(record)
    return records


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": BASE_URL,
        }
    )
    return session


def save_checkpoint(rows: List[Dict[str, object]], output_file: Path) -> None:
    write_csv(rows, output_file)


def fetch_text(session: requests.Session, url: str, backoff_seconds: float = DEFAULT_429_BACKOFF_SECONDS) -> str:
    last_error: Optional[Exception] = None
    wait_seconds = backoff_seconds
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code in {403, 429}:
                if attempt == REQUEST_RETRIES:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code} ao acessar {url}"
                    )
                time.sleep(wait_seconds + random.uniform(0, 5))
                wait_seconds = min(wait_seconds * 2, 300.0)
                continue
            response.raise_for_status()
            return response.text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < REQUEST_RETRIES:
                time.sleep(min(wait_seconds, 60.0) + random.uniform(0, 3))
                wait_seconds = min(wait_seconds * 1.5, 300.0)
    raise RuntimeError(f"Falha ao buscar {url}: {last_error}")


def scrape_search_page(
    session: requests.Session, page: int, template: str
) -> List[Dict[str, object]]:
    url = template.format(page=page)
    html = fetch_text(session, url)
    return parse_card_page(html)


def scrape_detail_page(session: requests.Session, url: str) -> Optional[Dict[str, object]]:
    html = fetch_text(session, url)
    return parse_detail_page(html)


def collect_live_records(
    target_records: int = DEFAULT_TARGET_RECORDS,
    max_pages: int = DEFAULT_MAX_PAGES,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    detail_delay_seconds: float = DEFAULT_DETAIL_DELAY_SECONDS,
    output_file: Path = OUTPUT_FILE,
) -> List[Dict[str, object]]:
    session = build_session()
    records_by_id: Dict[str, Dict[str, object]] = {}

    for template_index, template in enumerate(SEARCH_URL_TEMPLATES, start=1):
        source_name = template.split(BASE_URL, 1)[-1].split("?")[0].strip("/")
        print(f"Iniciando fonte {template_index}: {source_name}")

        for page in range(1, max_pages + 1):
            page_records = scrape_search_page(session, page, template)
            if not page_records:
                print(f"{source_name} página {page}: sem anúncios, encerrando fonte.")
                break

            new_cards = 0
            for card in page_records:
                listing_id = str(card.get("listing_id", "")).strip()
                if not listing_id or listing_id in records_by_id:
                    continue

                enriched = dict(card)
                detail = None
                detail_url = str(card.get("url", "")).strip()
                if detail_url:
                    try:
                        detail = scrape_detail_page(session, detail_url)
                    except Exception as exc:  # noqa: BLE001
                        print(f"Detalhe falhou para {listing_id}: {exc}")

                if detail:
                    enriched.update(detail)

                records_by_id[listing_id] = enriched
                new_cards += 1

                if len(records_by_id) >= target_records:
                    break

                if detail_delay_seconds > 0:
                    time.sleep(detail_delay_seconds)

            print(
                f"{source_name} página {page}: +{new_cards} novos, total único {len(records_by_id)}"
            )
            save_checkpoint(list(records_by_id.values()), output_file)

            if len(records_by_id) >= target_records:
                break

            if delay_seconds > 0:
                time.sleep(delay_seconds)

        if len(records_by_id) >= target_records:
            break

    merged = list(records_by_id.values())
    merged.sort(key=lambda row: str(row.get("listing_id", "")))
    return merged


def load_existing_records(output_file: Path) -> Dict[str, Dict[str, object]]:
    if not output_file.exists():
        return {}

    with output_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        data: Dict[str, Dict[str, object]] = {}
        for row in reader:
            listing_id = str(row.get("listing_id", "")).strip()
            if listing_id:
                data[listing_id] = row
        return data


def parse_amenities(raw: str) -> List[str]:
    if not raw:
        return []
    return [item for item in raw.split("|") if item]


def parse_detail_page(text: str) -> Optional[Dict[str, object]]:
    clean_text = text.replace('\\"', '"')
    listing_id = find_listing_id(clean_text) or find_listing_id(text)
    if not listing_id:
        return None

    tipo = find_first(r'"unitTypes":\["([^"]+)"\]', clean_text) or find_first(
        r'"type":\{"name":"([^"]+)"\}', clean_text
    )
    amenities_raw = find_first(
        r'"infos":\{"amenities":"([^"]*)","bathrooms":"([^"]*)","bedrooms":"([^"]*)","suites":"([^"]*)","total_area":"([^"]*)","floor":([^,}]+).*?"parking_spaces":"([^"]*)"\}',
        clean_text,
    )
    info_match = re.search(
        r'"infos":\{"amenities":"([^"]*)","bathrooms":"([^"]*)","bedrooms":"([^"]*)","suites":"([^"]*)","total_area":"([^"]*)","floor":([^,}]+).*?"parking_spaces":"([^"]*)"\}',
        clean_text,
        re.S,
    )
    if info_match:
        amenities_raw = info_match.group(1)
        bathrooms = extract_number(info_match.group(2))
        bedrooms = extract_number(info_match.group(3))
        suites = extract_number(info_match.group(4))
        total_area = extract_number(info_match.group(5))
        floor_raw = info_match.group(6).strip()
        parking_spaces = extract_number(info_match.group(7))
    else:
        bathrooms = bedrooms = suites = total_area = parking_spaces = None
        floor_raw = ""

    tracking_address_match = re.search(
        r'"listingTrackingData":\{.*?"address":\{"country":"BR","state":"([^"]+)","city":"([^"]+)","zone":"[^"]*","neighborhood":"([^"]+)","street":"([^"]+)","streetNumber":"([^"]+)"',
        clean_text,
        re.S,
    )
    geo_match = re.search(
        r'"address":\{"city":"([^"]+)","stateAcronym":"([^"]+)","neighborhood":"([^"]+)","isApproximateLocation":(?:true|false),"streetNumber":"([^"]+)","street":"([^"]+)".*?"coordinates":\{"latitude":(-?\d+(?:\.\d+)?),"longitude":(-?\d+(?:\.\d+)?)\}',
        clean_text,
        re.S,
    )
    if tracking_address_match:
        cidade = tracking_address_match.group(2)
        bairro = tracking_address_match.group(3)
        rua = tracking_address_match.group(4)
        numero = tracking_address_match.group(5)
        estado_nome = tracking_address_match.group(1)
    else:
        cidade = bairro = rua = numero = ""
        estado_nome = ""

    if geo_match:
        cidade = cidade or geo_match.group(1)
        estado = geo_match.group(2) or estado_nome
        bairro = bairro or geo_match.group(3)
        numero = numero or geo_match.group(4)
        rua = rua or geo_match.group(5)
        latitude = extract_float(geo_match.group(6))
        longitude = extract_float(geo_match.group(7))
    else:
        estado = estado_nome
        latitude = longitude = None

    created_at = ""
    created_block = find_first(
        r'data-testid="listing-created-date">(.*?)</span>', clean_text
    )
    if created_block:
        created_text = strip_tags(created_block)
        created_match = re.search(
            r'Anúncio criado em\s*([0-9]{1,2} de [^,]+ de [0-9]{4})',
            created_text,
        )
        if created_match:
            created_at = parse_pt_date_to_iso(created_match.group(1))

    description = ""
    description_block = find_first(
        r'data-testid="description-content">(.*?)</p>', clean_text
    )
    if description_block:
        description = strip_tags(description_block)

    advertiser = normalize_text(
        find_first(r'"advertiser":\{.*?"name":"([^"]+)"', clean_text)
    )
    rating_text = find_first(r'data-testid="rating-container".*?(\d+(?:\.\d+)?/\d+\s*\(\d+)', clean_text)
    rating = extract_float(rating_text, 0.0) if rating_text else 0.0

    amenities = set(parse_amenities(amenities_raw))
    result = {
        "listing_id": listing_id,
        "apartamento_ou_casa": "Apartamento" if tipo == "APARTMENT" else "Casa" if tipo == "HOUSE" else tipo,
        "estado": estado,
        "cidade": cidade,
        "bairro": bairro,
        "rua": rua,
        "numero": numero,
        "suites": suites,
        "andar": extract_number(floor_raw),
        "metragem": total_area,
        "estacionamentos": parking_spaces,
        "latitude": latitude,
        "longitude": longitude,
        "endereco": compose_address(rua, numero, bairro, cidade, estado),
        "anuncio_criado": created_at,
        "descricao": description,
        "corretora": advertiser,
        "nota_media": rating,
    }

    for code, field in AMENITY_MAP.items():
        if field == "tem_deck":
            continue
        result[field] = code in amenities

    result["tem_deck"] = (
        "DECK" in amenities
        or "BARBECUE_GRILL" in amenities
        or "deck" in description.lower()
    )
    result["tem_salao_jogos"] = result.get("tem_salao_jogos", False) or any(
        token in description.lower() for token in ["salao de jogos", "salão de jogos"]
    )
    result["tem_quadra_campo"] = result.get("tem_quadra_campo", False) or any(
        token in description.lower() for token in ["quadra", "campo"]
    )
    result["tem_portaria_24h"] = result.get("tem_portaria_24h", False)
    result["tem_vista_pro_mar"] = result.get("tem_vista_pro_mar", False)
    result["tem_condominio_fechado"] = result.get("tem_condominio_fechado", False)
    result["tem_piscina"] = result.get("tem_piscina", False)
    result["tem_varanda"] = result.get("tem_varanda", False)
    result["tem_academia"] = result.get("tem_academia", False)
    result["tem_salao_festas"] = result.get("tem_salao_festas", False)

    return result


def parse_pt_date_to_iso(pt_date: str) -> str:
    months = {
        "janeiro": 1,
        "fevereiro": 2,
        "marco": 3,
        "março": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }
    match = re.search(r"(\d{1,2})\s+de\s+([A-Za-zçÇ]+)\s+de\s+(\d{4})", pt_date)
    if not match:
        return pt_date
    day, month_name, year = match.groups()
    month = months.get(month_name.lower())
    if not month:
        return pt_date
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"


def compose_address(rua: str, numero: str, bairro: str, cidade: str, estado: str) -> str:
    parts = []
    street = " ".join(part for part in [rua, numero] if part).strip()
    if street:
        parts.append(street)
    locality = ", ".join(part for part in [bairro, cidade] if part)
    if locality:
        parts.append(locality)
    if estado:
        parts.append(estado)
    return ", ".join(parts)


def merge_records(records: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    merged: Dict[str, Dict[str, object]] = {}
    for record in records:
        listing_id = str(record.get("listing_id", "")).strip()
        if not listing_id:
            continue
        if listing_id not in merged:
            merged[listing_id] = {}
        merged[listing_id].update(record)
    return list(merged.values())


def field_order() -> List[str]:
    return [
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


def write_csv(rows: List[Dict[str, object]], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    headers = field_order()
    with output_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraping de imóveis da VivaReal.")
    parser.add_argument(
        "--target-records",
        type=int,
        default=DEFAULT_TARGET_RECORDS,
        help="Quantidade alvo de registros únicos a coletar.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Limite máximo de páginas de busca.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Pausa em segundos entre páginas.",
    )
    parser.add_argument(
        "--detail-delay",
        type=float,
        default=DEFAULT_DETAIL_DELAY_SECONDS,
        help="Pausa em segundos entre requisições de detalhe.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_FILE,
        help="Arquivo CSV de saída.",
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        default=None,
        help="Se informado, usa os HTMLs locais em vez do site ao vivo.",
    )
    return parser.parse_args()


def collect_from_html_dir(html_dir: Path) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    if not html_dir.exists():
        return records

    for html_file in sorted(html_dir.glob("*.html")):
        text = html_file.read_text(encoding="utf-8", errors="ignore")
        if "group/card" in text:
            records.extend(parse_card_page(text))
        detail = parse_detail_page(text)
        if detail:
            records.append(detail)

    merged = merge_records(records)
    merged.sort(key=lambda row: str(row.get("listing_id", "")))
    return merged


def main() -> int:
    args = parse_args()

    if args.html_dir is not None:
        records = collect_from_html_dir(args.html_dir)
    else:
        records = collect_live_records(
            target_records=args.target_records,
            max_pages=args.max_pages,
            delay_seconds=args.delay,
            detail_delay_seconds=args.detail_delay,
            output_file=args.output,
        )

    write_csv(records, args.output)
    print(f"{len(records)} registros salvos em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
