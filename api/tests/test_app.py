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
    monkeypatch.setattr(app_module, "criar_lote_ingestao", lambda nome, linhas: 7)
    updates = []
    monkeypatch.setattr(app_module, "atualizar_lote_ingestao", lambda *args, **kwargs: updates.append((args, kwargs)))
    monkeypatch.setattr(app_module, "salvar_dados_postgres", lambda df, id_lote=None: len(df))

    client = TestClient(app_module.app)
    response = client.post(
        "/insertData",
        files={"file": ("dados.csv", "preco,area_m2\n500000,80\n", "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id_lote"] == 7
    assert payload["linhas_recebidas"] == 1
    assert payload["linhas_salvas"] == 1
    assert updates[-1][1]["status"] == "sucesso"


def test_predict_usa_modelo_carregado(monkeypatch):
    monkeypatch.setattr(app_module, "modelo_carregado", FakeModel())
    monkeypatch.setattr(app_module, "explicar_predicao", lambda dados: [{"feature": "area_m2"}])

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
    assert response.json()["explicacao"] == [{"feature": "area_m2"}]


def test_train_models_cria_experimento_assincrono(monkeypatch):
    added = []

    class FakeBackgroundTasks:
        def add_task(self, fn, *args, **kwargs):
            added.append((fn, args, kwargs))

    monkeypatch.setattr(app_module, "validar_requisicao_treino", lambda request: ["ridge"])
    monkeypatch.setattr(app_module, "criar_experimento_treino", lambda request, modelos: 42)

    response = app_module.train_models(
        FakeBackgroundTasks(),
        app_module.TrainRequest(modelos=["ridge"], tipo_busca="grid", param_grids={"ridge": {"alpha": [1.0]}}),
    )

    assert response["id_experimento"] == 42
    assert response["status"] == "pendente"
    assert added[0][1][0] == 42


def test_data_rollback_retorna_estado(monkeypatch):
    monkeypatch.setattr(app_module, "rollback_lote", lambda id_lote: {"id_lote": id_lote, "status": "desativado"})

    assert app_module.data_rollback(9) == {"id_lote": 9, "status": "desativado"}


def test_ativar_modelo_recarrega_modelo(monkeypatch, tmp_path):
    model_path = tmp_path / "modelo.pkl"
    import joblib

    joblib.dump(FakeModel(), model_path)
    monkeypatch.setattr(
        app_module,
        "_fetchone",
        lambda query, params=(): {
            "id_modelo": 3,
            "caminho_artefato": str(model_path),
            "algoritmo": "Fake",
            "rmse": 1.0,
            "mae": 1.0,
            "r2": 1.0,
        },
    )
    monkeypatch.setattr(app_module, "_ensure_schema", lambda: None)

    class FakeCursor:
        def execute(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(app_module, "_get_connection", lambda: FakeConn())

    assert app_module.ativar_modelo(3)["id_modelo"] == 3
    assert isinstance(app_module.modelo_carregado, FakeModel)
