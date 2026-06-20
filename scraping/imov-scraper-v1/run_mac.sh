#!/usr/bin/env bash
set -e
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
python -m imov_scraper.cli --cidade Fortaleza --estado CE --sites zap,vivareal,imovelweb --finalidade venda --detalhar --max-detalhes 60
python scripts/quality_check.py saida/imoveis.json
