import importlib
import sys
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

SISTEMA_DIR = Path(__file__).resolve().parents[1]
if str(SISTEMA_DIR) not in sys.path:
    sys.path.insert(0, str(SISTEMA_DIR))

app_module = importlib.import_module("app")


class FakeModel:
    def predict(self, df):
        assert list(df.columns) == app_module.MODEL_FEATURES
        return [500000.0]


def test_insert_data_trata_csv_e_persiste_sem_banco_real(monkeypatch):
    tratado = pd.DataFrame(
        [
            {
                column: False if column in app_module.BOOLEAN_FEATURES else "x"
                for column in app_module.DB_COLUMNS
            }
        ]
    )
    tratado["area_m2"] = 80
    tratado["preco"] = 500000
    tratado["data_salvamento"] = pd.Timestamp("2026-06-22")

    class ResultadoFake:
        dados = tratado
        resumo_filtros = pd.DataFrame([{"etapa": "Inicial", "registros_restantes": 1}])

    monkeypatch.setattr(app_module, "tratar_imoveis", lambda df: ResultadoFake())
    monkeypatch.setattr(app_module, "salvar_dados_postgres", lambda df: len(df))

    client = TestClient(app_module.app)
    response = client.post(
        "/insertData",
        files={"file": ("dados.csv", "preco,area_m2\n500000,80\n", "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["linhas_recebidas"] == 1
    assert payload["linhas_salvas"] == 1


def test_predict_usa_modelo_carregado(monkeypatch):
    monkeypatch.setattr(app_module, "modelo_carregado", FakeModel())

    client = TestClient(app_module.app)
    response = client.post(
        "/predict",
        json={
            "bairro": "Aldeota",
            "area_m2": 80,
            "quartos": 3,
            "banheiros": 2,
            "suites": 1,
            "andar": 5,
            "vagas": 2,
            "tipo_imovel_padronizado": "apartamento_padrao",
        },
    )

    assert response.status_code == 200
    assert response.json()["preco_estimado"] == 500000.0
