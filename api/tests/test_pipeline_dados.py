from pathlib import Path

import pandas as pd

import importlib.util

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "pipeline_dados.py"
spec = importlib.util.spec_from_file_location("pipeline_dados", MODULE_PATH)
pipeline_dados = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline_dados)

BOOLEAN_FEATURES = pipeline_dados.BOOLEAN_FEATURES
MODEL_FEATURES = pipeline_dados.MODEL_FEATURES
criar_pre_processador = pipeline_dados.criar_pre_processador
preparar_dados_para_treino = pipeline_dados.preparar_dados_para_treino
tratar_imoveis = pipeline_dados.tratar_imoveis


def _raw_row(**overrides):
    row = {
        "listing_id": "abc-1",
        "titulo": "Apartamento no Meireles em Fortaleza",
        "apartamento_ou_casa": "apartamento",
        "tipo_imovel": "APARTMENT",
        "estado": "CE",
        "cidade": "Fortaleza",
        "bairro": "Dionisio Torres",
        "rua": "Rua Exemplo",
        "numero": "100",
        "endereco": "Rua Exemplo, Fortaleza",
        "metragem": 80,
        "quartos": 3,
        "banheiros": 2,
        "suites": 1,
        "andar": 7,
        "estacionamentos": 2,
        "preco_anuncio": 650000,
        "latitude": -3.73,
        "longitude": -38.50,
        "tem_portaria_24h": True,
        "tem_vista_pro_mar": False,
        "tem_condominio_fechado": True,
        "tem_piscina": True,
        "tem_deck": False,
        "tem_varanda_gourmet": True,
        "tem_varanda": True,
        "tem_academia": True,
        "tem_salao_festas": True,
        "tem_salao_jogos": False,
        "tem_quadra_campo": False,
        "descricao": "Imovel em Fortaleza",
        "anuncio_criado": "2026-06-10",
        "corretora": "Teste",
        "nota_media": 0,
        "url": "https://example.test/imovel",
    }
    row.update(overrides)
    return row


def test_tratar_imoveis_porta_logica_do_notebook_para_dataframe():
    raw = pd.DataFrame(
        [
            _raw_row(),
            _raw_row(listing_id="abc-2", tipo_imovel="COMMERCIAL_PROPERTY"),
        ]
    )

    resultado = tratar_imoveis(raw)

    assert len(resultado.dados) == 1
    tratado = resultado.dados.iloc[0]
    assert tratado["preco"] == 650000
    assert tratado["area_m2"] == 80
    assert tratado["bairro"] == "Dionisio Torres"
    assert tratado["tipo_imovel_padronizado"] == "apartamento_padrao"
    assert set(BOOLEAN_FEATURES).issubset(resultado.dados.columns)
    assert "Escopo residencial" in set(resultado.resumo_filtros["etapa"])


def test_preparar_dados_para_treino_salva_historico_e_cria_preprocessor(tmp_path):
    raw = pd.DataFrame([_raw_row()])
    caminho_historico = tmp_path / "historico.csv"

    X, y = preparar_dados_para_treino(raw, caminho_historico)
    preprocessor = criar_pre_processador()
    matriz = preprocessor.fit_transform(X)

    assert list(X.columns) == MODEL_FEATURES
    assert y.tolist() == [650000]
    assert caminho_historico.exists()
    assert matriz.shape[0] == 1
