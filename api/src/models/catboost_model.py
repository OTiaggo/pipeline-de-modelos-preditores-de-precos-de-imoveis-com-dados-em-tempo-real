from __future__ import annotations

from typing import Any

from sklearn.base import BaseEstimator

from .types import DEFAULT_RANDOM_STATE, ModelConfig


def _require_catboost() -> type[BaseEstimator]:
    try:
        from catboost import CatBoostRegressor
    except ImportError as exc:
        raise ImportError("Instale catboost para habilitar o modelo CatBoost.") from exc
    return CatBoostRegressor


def build_estimator(params: dict[str, Any]) -> BaseEstimator:
    CatBoostRegressor = _require_catboost()
    return CatBoostRegressor(
        loss_function="RMSE",
        eval_metric="RMSE",
        random_seed=DEFAULT_RANDOM_STATE,
        verbose=False,
        allow_writing_files=False,
        **params,
    )


def suggest_params(trial: Any) -> dict[str, Any]:
    return {
        "iterations": trial.suggest_int("iterations", 300, 1500),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.20, log=True),
        "depth": trial.suggest_int("depth", 4, 10),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 20.0, log=True),
        "bagging_temperature": trial.suggest_float("bagging_temperature", 0.0, 1.0),
        "random_strength": trial.suggest_float("random_strength", 0.0, 2.0),
    }


CONFIG = ModelConfig(
    "CatBoost",
    "optuna",
    build_estimator,
    suggest_params,
    use_native_categoricals=True,
    supports_early_stopping=True,
)
