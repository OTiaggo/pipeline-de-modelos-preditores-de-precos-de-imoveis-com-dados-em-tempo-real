from __future__ import annotations

from typing import Any

from sklearn.base import BaseEstimator
from sklearn.svm import SVR

from .types import ModelConfig


def build_estimator(params: dict[str, Any]) -> BaseEstimator:
    return SVR(**params)


def suggest_params(trial: Any) -> dict[str, Any]:
    return {
        "kernel": trial.suggest_categorical("kernel", ["rbf", "poly"]),
        "C": trial.suggest_float("C", 1.0, 500.0, log=True),
        "epsilon": trial.suggest_float("epsilon", 0.001, 1.0, log=True),
        "gamma": trial.suggest_categorical("gamma", ["scale", "auto"]),
    }


CONFIG = ModelConfig("SVR", "optuna", build_estimator, suggest_params)
