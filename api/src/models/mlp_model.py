from __future__ import annotations

from typing import Any

from sklearn.base import BaseEstimator
from sklearn.neural_network import MLPRegressor

from .types import DEFAULT_RANDOM_STATE, ModelConfig


def build_estimator(params: dict[str, Any]) -> BaseEstimator:
    return MLPRegressor(
        random_state=DEFAULT_RANDOM_STATE,
        early_stopping=True,
        max_iter=700,
        **params,
    )


def suggest_params(trial: Any) -> dict[str, Any]:
    width = trial.suggest_categorical("width", [64, 128, 256])
    depth = trial.suggest_int("depth", 1, 3)
    return {
        "hidden_layer_sizes": tuple([width] * depth),
        "activation": trial.suggest_categorical("activation", ["relu", "tanh"]),
        "alpha": trial.suggest_float("alpha", 1e-6, 1e-2, log=True),
        "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True),
        "batch_size": trial.suggest_categorical("batch_size", [32, 64, 128]),
    }


CONFIG = ModelConfig("MLPRegressor", "optuna", build_estimator, suggest_params)
