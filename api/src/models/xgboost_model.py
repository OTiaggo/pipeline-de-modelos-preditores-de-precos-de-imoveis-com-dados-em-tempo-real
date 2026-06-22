from __future__ import annotations

from typing import Any

from sklearn.base import BaseEstimator

from .types import DEFAULT_RANDOM_STATE, ModelConfig


def _require_xgboost() -> type[BaseEstimator]:
    try:
        from xgboost import XGBRegressor
    except ImportError as exc:
        raise ImportError("Instale xgboost para habilitar o modelo XGBoost.") from exc
    return XGBRegressor


def build_estimator(params: dict[str, Any]) -> BaseEstimator:
    XGBRegressor = _require_xgboost()
    return XGBRegressor(
        objective="reg:squarederror",
        eval_metric="rmse",
        random_state=DEFAULT_RANDOM_STATE,
        n_jobs=-1,
        verbosity=0,
        **params,
    )


def suggest_params(trial: Any) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 300, 1500),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.20, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 10.0),
        "subsample": trial.suggest_float("subsample", 0.60, 1.00),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.60, 1.00),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
    }


CONFIG = ModelConfig("XGBoost", "optuna", build_estimator, suggest_params, supports_early_stopping=True)
