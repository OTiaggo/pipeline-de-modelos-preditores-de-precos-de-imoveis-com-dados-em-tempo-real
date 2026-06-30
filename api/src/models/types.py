from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from sklearn.base import BaseEstimator


SearchStrategy = Literal["optuna", "grid"]

DEFAULT_RANDOM_STATE = 42
DEFAULT_N_SPLITS = 3
DEFAULT_N_TRIALS = 10
EARLY_STOPPING_ROUNDS = 50
CATEGORICAL_COLUMNS = ["bairro", "tipo_imovel_padronizado"]


@dataclass(frozen=True)
class ModelConfig:
    """Single registry entry.

    To include or remove a model, comment/uncomment one MODEL_REGISTRY line in
    models/registry.py. The training loop does not need to change.
    """

    display_name: str
    search_strategy: SearchStrategy
    build_estimator: Callable[[dict[str, Any]], BaseEstimator]
    suggest_params: Callable[[Any], dict[str, Any]] | None = None
    param_grid: dict[str, list[Any]] | None = None
    use_native_categoricals: bool = False
    supports_early_stopping: bool = False


@dataclass
class ModelSearchResult:
    model_key: str
    display_name: str
    best_params: dict[str, Any]
    rmse: float
    mae: float
    r2: float
    estimator: BaseEstimator
    search_strategy: SearchStrategy = "grid"
    duration_seconds: float = 0.0
