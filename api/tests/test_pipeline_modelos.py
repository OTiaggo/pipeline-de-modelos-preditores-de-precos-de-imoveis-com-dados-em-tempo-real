import importlib.util
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "pipeline_modelos.py"
spec = importlib.util.spec_from_file_location("pipeline_modelos", MODULE_PATH)
pipeline_modelos = importlib.util.module_from_spec(spec)
sys.modules["pipeline_modelos"] = pipeline_modelos
spec.loader.exec_module(pipeline_modelos)


class RowCountingRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, constant=0.0):
        self.constant = constant

    def fit(self, X, y):
        self.n_fit_rows_ = len(X)
        self.constant_ = float(pd.Series(y).mean())
        return self

    def predict(self, X):
        return np.full(len(X), self.constant_)


def test_model_registry_concentra_modelos_suportados():
    registry = pipeline_modelos.MODEL_REGISTRY

    assert {"xgboost", "lightgbm", "catboost", "random_forest", "ridge", "lasso", "svr", "mlp"}.issubset(registry)
    assert registry["catboost"].use_native_categoricals is True
    assert registry["ridge"].search_strategy == "grid"
    assert registry["xgboost"].search_strategy == "optuna"


def test_treinar_modelos_salva_campeao_com_registro_reduzido(tmp_path):
    X = pd.DataFrame(
        {
            "bairro": ["Aldeota", "Meireles", "Centro", "Aldeota", "Centro", "Meireles"],
            "tipo_imovel_padronizado": ["apartamento_padrao", "casa_padrao"] * 3,
            "area_m2": [60, 90, 45, 80, 55, 100],
            "quartos": [2, 3, 1, 3, 2, 4],
        }
    )
    y = pd.Series([420000, 650000, 250000, 590000, 310000, 760000])
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), ["bairro", "tipo_imovel_padronizado"]),
            ("numeric", "passthrough", ["area_m2", "quartos"]),
        ]
    )
    model_registry = {
        "ridge": pipeline_modelos.MODEL_REGISTRY["ridge"],
        "lasso": pipeline_modelos.MODEL_REGISTRY["lasso"],
    }

    champion, ranking = pipeline_modelos.treinar_modelos(
        X,
        y,
        preprocessor,
        caminho_modelo=tmp_path / "campeao.pkl",
        model_registry=model_registry,
        n_splits=3,
        n_trials=1,
    )

    assert champion.model_key in model_registry
    assert "model_key" in ranking.columns
    assert list(ranking["rmse"]) == sorted(ranking["rmse"])
    assert (tmp_path / "campeao.pkl").exists()


def test_treinar_modelos_aceita_subconjunto_e_grid_manual(tmp_path):
    X = pd.DataFrame(
        {
            "bairro": ["Aldeota", "Meireles", "Centro", "Aldeota", "Centro", "Meireles"],
            "tipo_imovel_padronizado": ["apartamento_padrao", "casa_padrao"] * 3,
            "area_m2": [60, 90, 45, 80, 55, 100],
            "quartos": [2, 3, 1, 3, 2, 4],
        }
    )
    y = pd.Series([420000, 650000, 250000, 590000, 310000, 760000])
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), ["bairro", "tipo_imovel_padronizado"]),
            ("numeric", "passthrough", ["area_m2", "quartos"]),
        ]
    )

    champion, ranking = pipeline_modelos.treinar_modelos(
        X,
        y,
        preprocessor,
        caminho_modelo=tmp_path / "campeao.pkl",
        model_registry={
            "ridge": pipeline_modelos.MODEL_REGISTRY["ridge"],
            "lasso": pipeline_modelos.MODEL_REGISTRY["lasso"],
        },
        model_keys=["ridge"],
        search_strategy="grid",
        param_grids={"ridge": {"alpha": [0.1, 1.0]}},
        n_splits=3,
        n_trials=1,
    )

    assert champion.model_key == "ridge"
    assert set(ranking["model_key"]) == {"ridge"}
    assert ranking.attrs["results"][0].search_strategy == "grid"


def test_treino_final_de_producao_refita_campeao_com_todos_os_dados(tmp_path):
    X = pd.DataFrame(
        {
            "bairro": ["Aldeota", "Meireles", "Centro", "Papicu", "Coco", "Benfica"],
            "tipo_imovel_padronizado": ["apartamento_padrao", "casa_padrao"] * 3,
            "area_m2": [60, 90, 45, 80, 55, 100],
            "quartos": [2, 3, 1, 3, 2, 4],
        }
    )
    y = pd.Series([420000, 650000, 250000, 590000, 310000, 760000])
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), ["bairro", "tipo_imovel_padronizado"]),
            ("numeric", "passthrough", ["area_m2", "quartos"]),
        ]
    )
    model_registry = {
        "contador": pipeline_modelos.ModelConfig(
            display_name="Contador",
            search_strategy="grid",
            build_estimator=lambda params: RowCountingRegressor(**params),
            param_grid={"constant": [0.0]},
            supports_early_stopping=True,
        )
    }

    champion, _ranking = pipeline_modelos.treinar_modelos(
        X,
        y,
        preprocessor,
        caminho_modelo=tmp_path / "campeao.pkl",
        model_registry=model_registry,
        n_splits=3,
        n_trials=1,
    )

    assert champion.estimator.named_steps["regressor"].n_fit_rows_ == len(X)

    modelo_salvo = joblib.load(tmp_path / "campeao.pkl")
    assert modelo_salvo.named_steps["regressor"].n_fit_rows_ == len(X)
