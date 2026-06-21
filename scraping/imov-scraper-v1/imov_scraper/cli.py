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


class CsvAutosave:
    def __init__(self, path: Path, batch_size=10):
        self.path = path
        self.batch_size = max(1, int(batch_size))
        self.buffer = []
        self.total = 0
        self.seen = set()
        if self.path.exists():
            self.path.unlink()

    def add(self, items):
        for item in items:
            key = (getattr(item, "url", None) or getattr(item, "external_id", None) or "").strip()
            if key and key in self.seen:
                continue
            if key:
                self.seen.add(key)
            self.buffer.append(item)
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        if not self.buffer:
            return
        append_csv(self.buffer, self.path)
        self.total += len(self.buffer)
        print(f"AUTOSAVE: {self.total} imóveis salvos em {self.path}")
        self.buffer.clear()


async def main():
    p = argparse.ArgumentParser(description="Scraper independente de imóveis via Playwright")
    p.add_argument("--cidade", help="Ex: Fortaleza")
    p.add_argument("--estado", help="UF, ex: CE")
    p.add_argument("--locais", help="Lista de pares Cidade/UF separados por vírgula, ex: Fortaleza/CE,Recife/PE")
    p.add_argument("--finalidade", default="venda", help="venda, aluguel ou venda,aluguel")
    p.add_argument("--sites", default="zap,vivareal,imovelweb", help="olx,zap,vivareal,imovelweb")
    p.add_argument("--out", default="saida/imoveis", help="Caminho base sem extensão")
    p.add_argument("--format", default="both", choices=["json", "csv", "both"], help="Formato de saída")
    p.add_argument("--detalhar", action="store_true", help="Abre cada anúncio individual para buscar descrição, endereço, IPTU e condomínio")
    p.add_argument("--max-detalhes", type=int, default=30, help="Máximo de anúncios a detalhar; use 0 para detalhar todos")
    p.add_argument("--detail-concurrency", type=int, default=2, help="Quantidade de páginas de detalhe abertas em paralelo")
    p.add_argument("--max-pages", type=int, default=5, help="Máximo de páginas por site e por localidade; use 0 para ir até não haver novos anúncios")
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
    autosave = None
    if args.format in {"csv", "both"}:
        autosave = CsvAutosave(base.with_name(f"{base.name}_autosave").with_suffix(".csv"), batch_size=10)

    items = []
    try:
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
                detail_concurrency=args.detail_concurrency,
                on_items=autosave.add if autosave else None,
            )
            items.extend(chunk)
    finally:
        if autosave:
            autosave.flush()

    if args.format in {"json", "both"}:
        save_json(items, base.with_suffix(".json"))
    if args.format in {"csv", "both"}:
        save_csv(items, base.with_suffix(".csv"))

    print(f"OK: {len(items)} imóveis novos coletados em {base.parent.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
