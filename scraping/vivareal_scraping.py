import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


URL = "https://www.vivareal.com.br/venda/ceara/fortaleza/?onde=%2CCear%C3%A1%2CFortaleza%2C%2C%2C%2C%2Ccity%2CBR%3ECeara%3ENULL%3EFortaleza%2C-3.73272%2C-38.527013%2C"
BASE_URL = "https://www.vivareal.com.br"
OUTPUT_FILE = "scraping/outputs/vivareal_fortaleza.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def get_text(element, selector: str, default: str = "") -> str:
    found = element.select_one(selector)
    if not found:
        return default
    return clean_text(found.get_text(" ", strip=True))


def extract_number(text: str, default: str = "") -> str:
    match = re.search(r"\d+", text or "")
    return match.group(0) if match else default


def extract_price(card) -> str:
    price = get_text(card, '[data-cy="rp-cardProperty-price-txt"] span')
    if not price:
        price = get_text(card, '[data-cy="rp-cardProperty-price-txt"]')
    return price.replace("R$", "").strip()


def extract_property_type(card) -> str:
    title = clean_text(card.get("title", ""))
    match = re.search(r"^(.*?)\s+para\s+", title, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()

    location = get_text(card, '[data-cy="rp-cardProperty-location-txt"]')
    match = re.search(r"^(.*?)\s+para\s+", location, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def extract_neighborhood(card) -> str:
    location = get_text(card, '[data-cy="rp-cardProperty-location-txt"]')
    if " em " in location:
        location = location.rsplit(" em ", 1)[1]

    neighborhood = location.split(",")[0].strip()
    if neighborhood:
        return neighborhood

    title = clean_text(card.get("title", ""))
    parts = [part.strip() for part in title.split(",")]
    return parts[-2] if len(parts) >= 2 else ""


def parse_card(card) -> dict:
    image = card.select_one('[data-cy="rp-cardProperty-image-img"] img, img')
    href = card.get("href", "")

    return {
        "Bairro": extract_neighborhood(card),
        "Tipo": extract_property_type(card),
        "Metragem": extract_number(get_text(card, '[data-cy="rp-cardProperty-propertyArea-txt"]')),
        "Quartos": extract_number(get_text(card, '[data-cy="rp-cardProperty-bedroomQuantity-txt"]')),
        "Banheiros": extract_number(get_text(card, '[data-cy="rp-cardProperty-bathroomQuantity-txt"]')),
        "Vagas": extract_number(get_text(card, '[data-cy="rp-cardProperty-parkingSpacesQuantity-txt"]')),
        "Preco": extract_price(card),
        "Rua": get_text(card, '[data-cy="rp-cardProperty-street-txt"]'),
        "URL": urljoin(BASE_URL, href),
        "Imagem": image.get("src", "") if image else "",
    }


def scrape_vivareal(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    cards = [
        element
        for element in soup.find_all("a")
        if "group/card" in (element.get("class") or [])
    ]

    data = [parse_card(card) for card in cards]
    return pd.DataFrame(data)


def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


if __name__ == "__main__":
    page_html = fetch_page(URL)
    df = scrape_vivareal(page_html)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"{len(df)} imoveis salvos em {OUTPUT_FILE}")
