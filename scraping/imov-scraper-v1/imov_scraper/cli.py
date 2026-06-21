import argparse
import asyncio
import csv
import json
from dataclasses import asdict
from pathlib import Path

from .core import scrape


FIELDS = [
    "external_id", "site", "finalidade", "tipo", "titulo", "preco", "preco_m2",
    "area_m2", "quartos", "banheiros", "vagas", "suites", "andar", "numero_endereco",
    "bairro", "cidade", "estado", "condominio", "iptu", "endereco", "descricao",
    "portaria", "vista_mar", "condominio_fechado", "piscina", "deck",
    "varanda_gourmet", "varanda", "academia", "salao_festa", "salao_jogos",
    "quadra_campo", "latitude", "longitude", "is_lancamento", "data_coleta", "url",
]

OLX_LIVE_FIELDS = [
    "listing_id", "titulo", "apartamento_ou_casa", "tipo_imovel", "estado",
    "cidade", "bairro", "rua", "numero", "endereco", "metragem", "quartos",
    "banheiros", "suites", "andar", "estacionamentos", "preco_anuncio",
    "latitude", "longitude", "tem_portaria_24h", "tem_vista_pro_mar",
    "tem_condominio_fechado", "tem_piscina", "tem_deck",
    "tem_varanda_gourmet", "tem_varanda", "tem_academia",
    "tem_salao_festas", "tem_salao_jogos", "tem_quadra_campo", "descricao",
    "anuncio_criado", "corretora", "nota_media", "url", "imagem_url",
]


def _listing_id_from_url(url: str) -> str:
    import hashlib
    import re

    url = url or ""
    m = re.search(r"(?:id-|/)(\d{8,13})(?:[/?#.-]|$)", url)
    if m:
        return m.group(1)
    return str(int(hashlib.md5(url.encode()).hexdigest()[:12], 16)) if url else ""


def _bool_cell(value):
    if value is None:
        return ""
    return int(bool(value))


def _olx_live_row(item):
    r = asdict(item)
    tipo = (r.get("tipo") or "").strip().lower()
    return {
        "listing_id": _listing_id_from_url(r.get("url")) or str(r.get("external_id") or "").replace("olx_", ""),
        "titulo": r.get("titulo") or "",
        "apartamento_ou_casa": tipo if tipo in {"apartamento", "casa"} else "",
        "tipo_imovel": tipo,
        "estado": r.get("estado") or "",
        "cidade": r.get("cidade") or "",
        "bairro": r.get("bairro") or "",
        "rua": r.get("rua") or "",
        "numero": r.get("numero") or r.get("numero_endereco") or "",
        "endereco": r.get("endereco") or "",
        "metragem": r.get("area_m2") or "",
        "quartos": r.get("quartos") or "",
        "banheiros": r.get("banheiros") or "",
        "suites": r.get("suites") or "",
        "andar": r.get("andar") if r.get("andar") is not None else "",
        "estacionamentos": r.get("vagas") or "",
        "preco_anuncio": r.get("preco") or "",
        "latitude": r.get("latitude") or "",
        "longitude": r.get("longitude") or "",
        "tem_portaria_24h": _bool_cell(r.get("portaria")),
        "tem_vista_pro_mar": _bool_cell(r.get("vista_mar")),
        "tem_condominio_fechado": _bool_cell(r.get("condominio_fechado")),
        "tem_piscina": _bool_cell(r.get("piscina")),
        "tem_deck": _bool_cell(r.get("deck")),
        "tem_varanda_gourmet": _bool_cell(r.get("varanda_gourmet")),
        "tem_varanda": _bool_cell(r.get("varanda")),
        "tem_academia": _bool_cell(r.get("academia")),
        "tem_salao_festas": _bool_cell(r.get("salao_festa")),
        "tem_salao_jogos": _bool_cell(r.get("salao_jogos")),
        "tem_quadra_campo": _bool_cell(r.get("quadra_campo")),
        "descricao": r.get("descricao") or "",
        "anuncio_criado": r.get("anuncio_criado") or "",
        "corretora": r.get("corretora") or "",
        "nota_media": r.get("nota_media") if r.get("nota_media") is not None else "",
        "url": r.get("url") or "",
        "imagem_url": r.get("imagem_url") or "",
    }


def save_olx_live_csv(items, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in items:
        r = asdict(item)
        if (r.get("site") or "").upper() != "OLX":
            continue
        if (r.get("finalidade") or "").lower() != "venda":
            continue
        if (r.get("cidade") or "").strip().lower() != "fortaleza":
            continue
        if (r.get("tipo") or "").strip().lower() not in {"apartamento", "casa"}:
            continue
        rows.append(_olx_live_row(item))
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OLX_LIVE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def save_json(items, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(x) for x in items], ensure_ascii=False, indent=2), encoding="utf-8")


def save_csv(items, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(x) for x in items]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_csv(items, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows([asdict(x) for x in items])


async def main():
    p = argparse.ArgumentParser(description="Scraper independente de imóveis via Playwright")
    p.add_argument("--cidade", help="Ex: Fortaleza")
    p.add_argument("--estado", help="UF, ex: CE")
    p.add_argument("--locais", help="Lista de pares Cidade/UF separados por vírgula, ex: Fortaleza/CE,Recife/PE")
    p.add_argument("--finalidade", default="venda", help="venda, aluguel ou venda,aluguel")
    p.add_argument("--sites", default="zap,vivareal,imovelweb", help="olx,zap,vivareal,imovelweb")
    p.add_argument("--out", default="saida/imoveis", help="Caminho base sem extensão")
    p.add_argument("--format", default="both", choices=["json", "csv", "both"], help="Formato de saída")
    p.add_argument("--schema", default="default", choices=["default", "olx_live"], help="Schema de exportacao CSV")
    p.add_argument("--detalhar", action="store_true", help="Abre cada anúncio individual para buscar descrição, endereço, IPTU e condomínio")
    p.add_argument("--max-detalhes", type=int, default=30, help="Máximo de anúncios a detalhar")
    p.add_argument("--max-pages", type=int, default=5, help="Máximo de páginas por site e por localidade")
    p.add_argument("--olx-start-page", type=int, default=1, help="Página inicial para a OLX quando estiver retomando uma coleta")
    p.add_argument("--sweep-bairros", action="store_true", help="Em Fortaleza/CE, varre bairros da cidade via OLX para aumentar volume")
    p.add_argument("--include-lancamentos", action="store_true", help="Mantém páginas de lançamentos/construtoras")
    p.add_argument("--include-sem-url", action="store_true", help="Mantém registros sem URL")
    p.add_argument("--skip-quality-filter", action="store_true", help="Mantém a coleta bruta sem deduplicar/filtrar registros")
    p.add_argument("--geocode", action="store_true", help="Busca latitude/longitude por bairro via Nominatim/OpenStreetMap")
    args = p.parse_args()

    finalidades = [x.strip() for x in args.finalidade.split(",") if x.strip()]
    sites = [x.strip() for x in args.sites.split(",") if x.strip()]

    locais = []
    if args.locais:
        for raw in args.locais.split(","):
            raw = raw.strip()
            if not raw:
                continue
            if "/" not in raw:
                p.error(f"Localidade inválida: {raw}. Use Cidade/UF.")
            cidade, estado = [part.strip() for part in raw.rsplit("/", 1)]
            if not cidade or not estado:
                p.error(f"Localidade inválida: {raw}. Use Cidade/UF.")
            locais.append((cidade, estado.upper()))
    else:
        if not args.cidade or not args.estado:
            p.error("Informe --cidade e --estado, ou use --locais.")
        locais.append((args.cidade, args.estado.upper()))

    base = Path(args.out)
    items = []
    for cidade, estado in locais:
        chunk = await scrape(
            cidade,
            estado,
            finalidades=finalidades,
            sites=sites,
            detalhar=args.detalhar,
            max_detalhes=args.max_detalhes,
            include_lancamentos=args.include_lancamentos,
            include_sem_url=args.include_sem_url,
            geocode=args.geocode,
            max_pages=args.max_pages,
            sweep_bairros=args.sweep_bairros,
            olx_start_page=args.olx_start_page,
            skip_quality_filter=args.skip_quality_filter,
        )
        items.extend(chunk)

    if args.schema == "olx_live":
        total = save_olx_live_csv(items, base.with_suffix(".csv"))
        print(f"OK: {total} imoveis OLX salvos em {base.with_suffix('.csv').resolve()}")
        return

    if args.format in {"json", "both"}:
        save_json(items, base.with_suffix(".json"))
    if args.format in {"csv", "both"}:
        append_csv(items, base.with_suffix(".csv"))

    print(f"OK: {len(items)} imóveis novos coletados em {base.parent.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
