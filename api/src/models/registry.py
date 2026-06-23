from __future__ import annotations

from .catboost_model import CONFIG as CATBOOST_CONFIG
from .lasso_model import CONFIG as LASSO_CONFIG
from .lightgbm_model import CONFIG as LIGHTGBM_CONFIG
from .mlp_model import CONFIG as MLP_CONFIG
from .random_forest_model import CONFIG as RANDOM_FOREST_CONFIG
from .ridge_model import CONFIG as RIDGE_CONFIG
from .svr_model import CONFIG as SVR_CONFIG
from .types import ModelConfig
from .xgboost_model import CONFIG as XGBOOST_CONFIG


# Model registry:
# To remove a model from training, comment only its line below.
# To add a model, create sistema/src/models/<model_name>.py and add one entry
# here. The training loop in utils/training.py does not need to change.
MODEL_REGISTRY: dict[str, ModelConfig] = {
    "xgboost": XGBOOST_CONFIG,
    "lightgbm": LIGHTGBM_CONFIG,
    "catboost": CATBOOST_CONFIG,
    "random_forest": RANDOM_FOREST_CONFIG,
    "ridge": RIDGE_CONFIG,
    "lasso": LASSO_CONFIG,
    "svr": SVR_CONFIG,
    "mlp": MLP_CONFIG,
    # "gwr": ...,  # Placeholder: GWR needs a spatial stack outside standard sklearn.
}
