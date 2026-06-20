# Imov Scraper v1

Scraper independente para coletar anúncios de imóveis em Fortaleza/CE.

Esta v1 foi fechada com foco em **dados finais consistentes** para análise, BI ou uso em outro projeto Python. Ela mantém ZAP Imóveis, VivaReal e ImovelWeb, mas aplica limpeza e validação antes de salvar os arquivos.

## O que esta v1 faz

- Coleta anúncios de venda/aluguel em ZAP, VivaReal e ImovelWeb.
- Abre anúncios individuais quando usado com `--detalhar`.
- Extrai, quando disponível:
  - site
  - URL
  - título
  - finalidade
  - tipo do imóvel
  - preço
  - preço por m²
  - área
  - quartos
  - banheiros
  - vagas
  - bairro
  - cidade
  - estado
  - condomínio
  - IPTU
  - descrição
  - endereço
  - data da coleta
- Corrige bairros de Fortaleza usando lista controlada.
- Remove registros sem preço, sem bairro, sem URL ou muito inconsistentes.
- Deduplica anúncios repetidos entre portais.
- Exporta CSV e JSON.

> Latitude e longitude ficaram fora da v1 por enquanto.

## Instalação no Mac

Entre na pasta do projeto e rode:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

## Rodar coleta principal

```bash
python -m imov_scraper.cli --cidade Fortaleza --estado CE --sites zap,vivareal,imovelweb --finalidade venda --detalhar --max-detalhes 60
```

## Arquivos gerados

Por padrão, os arquivos saem em:

```text
saida/imoveis.csv
saida/imoveis.json
```

## Checar qualidade da saída

Depois da coleta:

```bash
python scripts/quality_check.py saida/imoveis.json
```

O script mostra:

- total de imóveis
- quantidade por site
- registros sem bairro
- registros sem área
- URLs vazias
- bairros suspeitos
- bairros com número grudado
- tipo suspeito
- preço/m² fora de escala

## Usar como biblioteca Python

```python
from imov_scraper import scrape_sync

imoveis = scrape_sync(
    cidade="Fortaleza",
    estado="CE",
    finalidades=["venda"],
    sites=["zap", "vivareal", "imovelweb"],
    detalhar=True,
    max_detalhes=60,
)

for imovel in imoveis[:5]:
    print(imovel.bairro, imovel.tipo, imovel.preco, imovel.url)
```

## Observações

Scraping pode variar porque os portais mudam layout, bloqueios e carregamento. A v1 prioriza consistência da base final: é melhor retornar menos imóveis bons do que muitos registros sujos.
