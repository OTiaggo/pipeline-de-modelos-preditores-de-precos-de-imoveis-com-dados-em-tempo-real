import argparse
import csv
import json
import re
from pathlib import Path

BAD_BAIRROS = [
    'tamanho do imóvel', 'tamanho do imovel', 'destaque', 'super destaque',
    'imobiliária', 'imobiliaria', 'corretores', 'transações', 'transacoes', 'ltda'
]
NEGATIVE_TITLES = ['ar condicionado', 'ar-condicionado', 'mesa', 'bicicleta', 'bike', 'sapatilha', 'cadeira']


def load(path: Path):
    if path.suffix.lower() == '.json':
        return json.loads(path.read_text(encoding='utf-8'))
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def num(x):
    try:
        if x in (None, ''): return None
        return float(str(x).replace(',', '.'))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description='Checa rapidamente a qualidade da saída do scraper.')
    ap.add_argument('arquivo', help='CSV ou JSON gerado pelo scraper')
    args = ap.parse_args()
    rows = load(Path(args.arquivo))
    total = len(rows)
    by_site = {}
    for r in rows:
        by_site[r.get('site','')] = by_site.get(r.get('site',''), 0) + 1

    bad_olx = [r for r in rows if r.get('site') == 'OLX' and any(w in str(r.get('titulo','')).lower() for w in NEGATIVE_TITLES)]
    bad_bairro = [r for r in rows if any(w in str(r.get('bairro','')).lower() for w in BAD_BAIRROS)]
    bairro_com_numero = [r for r in rows if re.search(r'\d', str(r.get('bairro','')))]
    no_url = [r for r in rows if not r.get('url')]
    no_bairro = [r for r in rows if not r.get('bairro')]
    no_area = [r for r in rows if not r.get('area_m2')]
    tipo_suspeito = [r for r in rows if r.get('tipo') in ('outro','comercial') and (num(r.get('quartos')) or 0) >= 2 and 'comercial' not in str(r.get('titulo','')).lower()]
    preco_m2_ruim = []
    for r in rows:
        pm2 = num(r.get('preco_m2'))
        if pm2 and (pm2 < 300 or pm2 > 35000):
            preco_m2_ruim.append(r)

    print(f'Total: {total}')
    print('Por site:', by_site)
    if total:
        print(f'Sem bairro: {len(no_bairro)} ({len(no_bairro)/total:.1%})')
        print(f'Sem área: {len(no_area)} ({len(no_area)/total:.1%})')
    print(f'URL vazia: {len(no_url)}')
    print(f'Bairro suspeito: {len(bad_bairro)}')
    print(f'Bairro com número grudado: {len(bairro_com_numero)}')
    print(f'Tipo suspeito: {len(tipo_suspeito)}')
    print(f'Preço/m² fora de escala: {len(preco_m2_ruim)}')
    print(f'OLX não-imóvel provável: {len(bad_olx)}')

    def show(title, arr):
        if arr[:5]:
            print('\n' + title)
            for r in arr[:5]:
                print('-', r.get('site'), '|', r.get('tipo'), '|', r.get('bairro'), '|', r.get('titulo'), '|', r.get('url'))

    show('Exemplos de bairro com número:', bairro_com_numero)
    show('Exemplos de tipo suspeito:', tipo_suspeito)
    show('Exemplos de bairro suspeito:', bad_bairro)


if __name__ == '__main__':
    main()
