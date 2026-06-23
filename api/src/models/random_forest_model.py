from __future__ import annotations

from typing import Any

from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestRegressor

from .types import DEFAULT_RANDOM_STATE, ModelConfig


def build_estimator(params: dict[str, Any]) -> BaseEstimator:
    return RandomForestRegressor(random_state=DEFAULT_RANDOM_STATE, n_jobs=-1, **params)


def suggest_params(trial: Any) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 200, 900, step=100),
        "max_depth": trial.suggest_int("max_depth", 4, 32),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", 1.0]),
    }


CONFIG = ModelConfig("Random Forest", "optuna", build_estimator, suggest_params)
