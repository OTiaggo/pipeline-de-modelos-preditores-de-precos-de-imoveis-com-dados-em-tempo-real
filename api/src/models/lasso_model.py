from __future__ import annotations

from typing import Any

from sklearn.base import BaseEstimator
from sklearn.linear_model import Lasso

from .types import DEFAULT_RANDOM_STATE, ModelConfig


def build_estimator(params: dict[str, Any]) -> BaseEstimator:
    return Lasso(random_state=DEFAULT_RANDOM_STATE, max_iter=10_000, **params)


CONFIG = ModelConfig(
    "Lasso",
    "grid",
    build_estimator,
    param_grid={"alpha": [0.001, 0.01, 0.1, 1.0, 10.0]},
)
