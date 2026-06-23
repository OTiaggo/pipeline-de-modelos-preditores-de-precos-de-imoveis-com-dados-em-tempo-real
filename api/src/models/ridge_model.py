from __future__ import annotations

from typing import Any

from sklearn.base import BaseEstimator
from sklearn.linear_model import Ridge

from .types import DEFAULT_RANDOM_STATE, ModelConfig


def build_estimator(params: dict[str, Any]) -> BaseEstimator:
    return Ridge(random_state=DEFAULT_RANDOM_STATE, **params)


CONFIG = ModelConfig(
    "Ridge",
    "grid",
    build_estimator,
    param_grid={"alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
)
