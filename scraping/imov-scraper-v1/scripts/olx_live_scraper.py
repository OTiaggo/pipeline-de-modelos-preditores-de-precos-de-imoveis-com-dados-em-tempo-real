import argparse
import csv
import html
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from imov_scraper.core import _extract_features  # noqa: E402


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

BASE_URLS = [
    ("apartamento", "imoveis/venda/apartamentos/estado-ce/fortaleza-e-regiao"),
    ("casa", "imoveis/venda/casas/estado-ce/fortaleza-e-regiao"),
]


def fetch(url: str) -> str:
    cmd = [
        "curl.exe",
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
        "40",
        "-sS",
    ]
    return subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")


def next_data(html_text: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text)
    if not m:
        return {}
    return json.loads(html.unescape(m.group(1)))


def discover_build_id() -> str:
    html_text = fetch("https://www.olx.com.br/imoveis/venda/apartamentos/estado-ce/fortaleza-e-regiao")
    data = next_data(html_text)
    build_id = data.get("buildId")
    if not build_id:
        raise RuntimeError("buildId da OLX nao encontrado")
    return build_id


def fetch_page_props(build_id: str, path: str, page: int) -> dict:
    suffix = f"?o={page}" if page > 1 else ""
    url = f"https://www.olx.com.br/_next/data/{build_id}/{path}.json{suffix}"
    try:
        data = json.loads(fetch(url))
        return data.get("pageProps") or {}
    except Exception:
        fallback_url = f"https://www.olx.com.br/{path}{suffix}"
        data = next_data(fetch(fallback_url))
        return ((data.get("props") or {}).get("pageProps") or {})


def money_to_float(value):
    if value in (None, ""):
        return ""
    m = re.search(r"([\d.]+)(?:,\d{1,2})?", str(value))
    return float(m.group(1).replace(".", "")) if m else ""


def first_int(value):
    if value in (None, ""):
        return ""
    m = re.search(r"\d+", str(value))
    return int(m.group(0)) if m else ""


def bool_cell(value):
    return int(bool(value))


def prop_map(ad: dict) -> dict:
    out = {}
    for p in ad.get("properties") or []:
        name = p.get("name")
        if name:
            out[name] = p.get("value")
    return out


def split_location(location: str):
    parts = [p.strip() for p in (location or "").split(",", 1)]
    if len(parts) == 2:
        return parts[0], parts[1].split("-")[0].strip()
    return "", ""


def image_url(ad: dict) -> str:
    images = ad.get("images") or []
    if not images:
        return ""
    img = images[0] or {}
    return img.get("original") or img.get("originalWebp") or ""


def ad_date(ad: dict) -> str:
    raw = ad.get("date")
    if isinstance(raw, (int, float)) and raw > 0:
        return datetime.fromtimestamp(raw, tz=timezone.utc).isoformat(timespec="seconds")
    return ""


def normalize_row(ad: dict, kind: str) -> dict:
    props = prop_map(ad)
    cidade, bairro = split_location(ad.get("location") or "")
    feature_text = " ".join([
        str(ad.get("subject") or ""),
        str(props.get("re_features") or ""),
        str(props.get("re_types") or ""),
    ])
    feats = _extract_features(feature_text)
    tipo_imovel = props.get("real_estate_type") or ad.get("categoryName") or kind
    rating = ad.get("userGoogleRating") if ad.get("userGoogleReviewsVisible") else ""
    return {
        "listing_id": str(ad.get("listId") or ""),
        "titulo": ad.get("subject") or "",
        "apartamento_ou_casa": kind,
        "tipo_imovel": tipo_imovel,
        "estado": "CE",
        "cidade": cidade,
        "bairro": bairro,
        "rua": "",
        "numero": "",
        "endereco": "",
        "metragem": first_int(props.get("size")),
        "quartos": first_int(props.get("rooms")),
        "banheiros": first_int(props.get("bathrooms")),
        "suites": first_int(props.get("suites")),
        "andar": first_int(props.get("floor")),
        "estacionamentos": first_int(props.get("garage_spaces")),
        "preco_anuncio": money_to_float(ad.get("priceValue") or ad.get("price")),
        "latitude": "",
        "longitude": "",
        "tem_portaria_24h": bool_cell(feats.get("portaria")),
        "tem_vista_pro_mar": bool_cell(feats.get("vista_mar")),
        "tem_condominio_fechado": bool_cell(feats.get("condominio_fechado")),
        "tem_piscina": bool_cell(feats.get("piscina")),
        "tem_deck": bool_cell(feats.get("deck")),
        "tem_varanda": bool_cell(feats.get("varanda")),
        "tem_academia": bool_cell(feats.get("academia")),
        "tem_salao_festas": bool_cell(feats.get("salao_festa")),
        "tem_salao_jogos": bool_cell(feats.get("salao_jogos")),
        "tem_quadra_campo": bool_cell(feats.get("quadra_campo")),
        "descricao": "",
        "anuncio_criado": ad_date(ad),
        "corretora": "",
        "nota_media": rating or "",
        "url": ad.get("url") or "",
        "imagem_url": image_url(ad),
    }


def collect(limit: int, max_pages: int, delay: float):
    rows = []
    seen = set()
    build_id = discover_build_id()
    print(f"[OLX] buildId={build_id}", flush=True)
    for kind, path in BASE_URLS:
        empty_streak = 0
        for page in range(1, max_pages + 1):
            print(f"[OLX] {kind} p{page}: {len(rows)}/{limit}", flush=True)
            try:
                page_props = fetch_page_props(build_id, path, page)
            except Exception as exc:
                print(f"[OLX] falhou {kind} p{page}: {exc}", flush=True)
                break
            ads = page_props.get("ads") or []
            if not ads:
                break
            added = 0
            for ad in ads:
                row = normalize_row(ad, kind)
                if row["cidade"].strip().lower() != "fortaleza":
                    continue
                if not row["listing_id"] or row["listing_id"] in seen:
                    continue
                if not row["preco_anuncio"]:
                    continue
                seen.add(row["listing_id"])
                rows.append(row)
                added += 1
                if len(rows) >= limit:
                    return rows
            print(f"[OLX] {kind} p{page}: {added} Fortaleza", flush=True)
            if added == 0:
                empty_streak += 1
                if empty_streak >= 5:
                    print(f"[OLX] {kind}: parada apos {empty_streak} paginas sem novos registros", flush=True)
                    break
            else:
                empty_streak = 0
            time.sleep(delay)
    return rows


def main():
    ap = argparse.ArgumentParser(description="Coleta OLX live para Fortaleza/CE no schema olx_live.")
    ap.add_argument("--out", default=str(ROOT / "saida" / "olx_live_10k.csv"))
    ap.add_argument("--limit", type=int, default=20000)
    ap.add_argument("--max-pages", type=int, default=400)
    ap.add_argument("--delay", type=float, default=0.4)
    args = ap.parse_args()

    rows = collect(limit=args.limit, max_pages=args.max_pages, delay=args.delay)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"OK: {len(rows)} linhas salvas em {out.resolve()}")


if __name__ == "__main__":
    main()
