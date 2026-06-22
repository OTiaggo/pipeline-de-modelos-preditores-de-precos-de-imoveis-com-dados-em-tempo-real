from __future__ import annotations

from typing import Any

from sklearn.base import BaseEstimator

from .types import DEFAULT_RANDOM_STATE, ModelConfig


def _require_lightgbm() -> type[BaseEstimator]:
    try:
        from lightgbm import LGBMRegressor
    except ImportError as exc:
        raise ImportError("Instale lightgbm para habilitar o modelo LightGBM.") from exc
    return LGBMRegressor


def build_estimator(params: dict[str, Any]) -> BaseEstimator:
    LGBMRegressor = _require_lightgbm()
    return LGBMRegressor(
        objective="regression",
        random_state=DEFAULT_RANDOM_STATE,
        n_jobs=-1,
        verbose=-1,
        **params,
    )


def suggest_params(trial: Any) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 300, 1500),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.20, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 16, 256),
        "max_depth": trial.suggest_int("max_depth", 3, 14),
        "min_child_samples": trial.suggest_int("min_child_samples", 10, 100),
        "subsample": trial.suggest_float("subsample", 0.60, 1.00),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.60, 1.00),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
    }


CONFIG = ModelConfig("LightGBM", "optuna", build_estimator, suggest_params, supports_early_stopping=True)
