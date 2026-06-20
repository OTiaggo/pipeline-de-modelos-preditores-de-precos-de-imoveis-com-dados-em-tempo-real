from imov_scraper.core import scrape_sync, to_dicts

items = scrape_sync(
    "Fortaleza",
    "CE",
    sites=("zap", "vivareal", "imovelweb"),
    finalidades=("venda",),
    detalhar=True,
    max_detalhes=10,
)

print(f"Coletados: {len(items)}")
for item in items[:5]:
    print(item.site, item.tipo, item.bairro, item.preco, item.preco_m2, item.url)

# Caso queira converter para lista de dicionários:
rows = to_dicts(items)
