from __future__ import annotations

from pathlib import Path
from dataclasses import replace
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

try:
    import optuna
except ImportError:
    optuna = None

try:
    from ..models.registry import MODEL_REGISTRY
    from ..models.types import (
        CATEGORICAL_COLUMNS,
        DEFAULT_N_SPLITS,
        DEFAULT_N_TRIALS,
        DEFAULT_RANDOM_STATE,
        EARLY_STOPPING_ROUNDS,
        ModelConfig,
        ModelSearchResult,
    )
except ImportError:
    from models.registry import MODEL_REGISTRY
    from models.types import (
        CATEGORICAL_COLUMNS,
        DEFAULT_N_SPLITS,
        DEFAULT_N_TRIALS,
        DEFAULT_RANDOM_STATE,
        EARLY_STOPPING_ROUNDS,
        ModelConfig,
        ModelSearchResult,
    )


def _rmse(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _metrics(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "rmse": _rmse(y_true, y_pred),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def _prepare_catboost_features(X: pd.DataFrame) -> pd.DataFrame:
    X_cat = X.copy()
    for column in CATEGORICAL_COLUMNS:
        if column in X_cat.columns:
            X_cat[column] = X_cat[column].fillna("desconhecido").astype(str)
    return X_cat


def _make_pipeline(preprocessor: Any, estimator: BaseEstimator) -> Pipeline:
    return Pipeline(steps=[("preprocessor", clone(preprocessor)), ("regressor", estimator)])


def _fit_with_optional_early_stopping(
    estimator: BaseEstimator,
    X_train: pd.DataFrame | np.ndarray,
    y_train: pd.Series,
    X_valid: pd.DataFrame | np.ndarray,
    y_valid: pd.Series,
    *,
    config: ModelConfig,
    cat_features: list[str] | None = None,
) -> BaseEstimator:
    if not config.supports_early_stopping:
        estimator.fit(X_train, y_train)
        return estimator

    if config.display_name == "XGBoost":
        try:
            estimator.fit(
                X_train,
                y_train,
                eval_set=[(X_valid, y_valid)],
                early_stopping_rounds=EARLY_STOPPING_ROUNDS,
                verbose=False,
            )
        except TypeError:
            estimator.set_params(early_stopping_rounds=EARLY_STOPPING_ROUNDS)
            estimator.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
        return estimator

    if config.display_name == "LightGBM":
        try:
            from lightgbm import early_stopping, log_evaluation

            estimator.fit(
                X_train,
                y_train,
                eval_set=[(X_valid, y_valid)],
                eval_metric="rmse",
                callbacks=[early_stopping(EARLY_STOPPING_ROUNDS, verbose=False), log_evaluation(0)],
            )
        except TypeError:
            estimator.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], eval_metric="rmse")
        return estimator

    if config.display_name == "CatBoost":
        estimator.fit(
            X_train,
            y_train,
            eval_set=(X_valid, y_valid),
            cat_features=cat_features or [],
            early_stopping_rounds=EARLY_STOPPING_ROUNDS,
            verbose=False,
        )
        return estimator

    estimator.fit(X_train, y_train)
    return estimator


def _cross_validate_params(
    X: pd.DataFrame,
    y: pd.Series,
    preprocessor: Any,
    config: ModelConfig,
    params: dict[str, Any],
    cv: KFold,
) -> dict[str, float]:
    fold_metrics: list[dict[str, float]] = []

    for train_idx, valid_idx in cv.split(X, y):
        X_train, X_valid = X.iloc[train_idx], X.iloc[valid_idx]
        y_train, y_valid = y.iloc[train_idx], y.iloc[valid_idx]
        estimator = config.build_estimator(params)

        if config.use_native_categoricals:
            X_train_cat = _prepare_catboost_features(X_train)
            X_valid_cat = _prepare_catboost_features(X_valid)
            cat_features = [c for c in CATEGORICAL_COLUMNS if c in X_train_cat.columns]
            _fit_with_optional_early_stopping(
                estimator,
                X_train_cat,
                y_train,
                X_valid_cat,
                y_valid,
                config=config,
                cat_features=cat_features,
            )
            predictions = estimator.predict(X_valid_cat)
        else:
            fold_preprocessor = clone(preprocessor)
            X_train_ready = fold_preprocessor.fit_transform(X_train)
            X_valid_ready = fold_preprocessor.transform(X_valid)
            _fit_with_optional_early_stopping(
                estimator,
                X_train_ready,
                y_train,
                X_valid_ready,
                y_valid,
                config=config,
            )
            predictions = estimator.predict(X_valid_ready)

        fold_metrics.append(_metrics(y_valid, predictions))

    return {
        "rmse": float(np.mean([metric["rmse"] for metric in fold_metrics])),
        "mae": float(np.mean([metric["mae"] for metric in fold_metrics])),
        "r2": float(np.mean([metric["r2"] for metric in fold_metrics])),
    }


def _optimize_with_optuna(
    model_key: str,
    X: pd.DataFrame,
    y: pd.Series,
    preprocessor: Any,
    config: ModelConfig,
    cv: KFold,
    n_trials: int,
) -> tuple[dict[str, Any], dict[str, float]]:
    if optuna is None:
        raise ImportError("Instale optuna para usar busca bayesiana.")
    if config.suggest_params is None:
        raise ValueError(f"Modelo {model_key} nao define espaco Optuna.")

    def objective(trial: Any) -> float:
        params = config.suggest_params(trial)
        metrics = _cross_validate_params(X, y, preprocessor, config, params, cv)
        trial.set_user_attr("mae", metrics["mae"])
        trial.set_user_attr("r2", metrics["r2"])
        return metrics["rmse"]

    study = optuna.create_study(direction="minimize", study_name=f"{model_key}_rmse")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = dict(study.best_params)
    best_metrics = _cross_validate_params(X, y, preprocessor, config, best_params, cv)
    return best_params, best_metrics


def _optimize_with_grid(
    X: pd.DataFrame,
    y: pd.Series,
    preprocessor: Any,
    config: ModelConfig,
    cv: KFold,
) -> tuple[dict[str, Any], dict[str, float]]:
    if config.param_grid is None:
        raise ValueError(f"Modelo {config.display_name} nao define param_grid.")

    pipeline = _make_pipeline(preprocessor, config.build_estimator({}))
    grid = {f"regressor__{key}": value for key, value in config.param_grid.items()}
    search = GridSearchCV(
        pipeline,
        param_grid=grid,
        scoring="neg_root_mean_squared_error",
        cv=cv,
        n_jobs=-1,
        refit=True,
    )
    search.fit(X, y)

    best_params = {
        key.replace("regressor__", ""): value
        for key, value in search.best_params_.items()
    }
    best_metrics = _cross_validate_params(X, y, preprocessor, config, best_params, cv)
    return best_params, best_metrics


def _fit_final_estimator(
    X: pd.DataFrame,
    y: pd.Series,
    preprocessor: Any,
    config: ModelConfig,
    params: dict[str, Any],
) -> BaseEstimator:
    """Fit the production artifact with all available training rows.

    Cross-validation and optional early stopping are used during model
    selection. After the champion hyperparameters are known, the artifact saved
    for the API is refit on the full dataset so no recent production data is
    left out of the deployed model.
    """

    estimator = config.build_estimator(params)

    if config.use_native_categoricals:
        X_cat = _prepare_catboost_features(X)
        cat_features = [c for c in CATEGORICAL_COLUMNS if c in X_cat.columns]
        estimator.fit(X_cat, y, cat_features=cat_features)
        return Pipeline(
            steps=[
                ("prepare_catboost_categories", FunctionTransformer(_prepare_catboost_features, validate=False)),
                ("regressor", estimator),
            ]
        )

    pipeline = _make_pipeline(preprocessor, estimator)
    pipeline.fit(X, y)
    return pipeline


def treinar_modelos(
    X: pd.DataFrame,
    y: pd.Series,
    preprocessor: Any,
    *,
    caminho_modelo: str | Path,
    model_registry: dict[str, ModelConfig] | None = None,
    model_keys: list[str] | None = None,
    search_strategy: str | None = None,
    param_grids: dict[str, dict[str, list[Any]]] | None = None,
    n_splits: int = DEFAULT_N_SPLITS,
    n_trials: int = DEFAULT_N_TRIALS,
) -> tuple[ModelSearchResult, pd.DataFrame]:
    registry = model_registry or MODEL_REGISTRY
    if model_keys:
        missing = [model_key for model_key in model_keys if model_key not in registry]
        if missing:
            raise ValueError(f"Modelos nao suportados: {missing}")
        registry = {model_key: registry[model_key] for model_key in model_keys}

    cv = KFold(n_splits=n_splits, shuffle=True, random_state=DEFAULT_RANDOM_STATE)
    results: list[ModelSearchResult] = []
    grids = param_grids or {}

    for model_key, config in registry.items():
        print(f"\n=== Otimizando {config.display_name} ===")
        started_at = time.perf_counter()
        try:
            effective_config = config
            if model_key in grids:
                effective_config = replace(config, search_strategy="grid", param_grid=grids[model_key])

            requested_strategy = (search_strategy or effective_config.search_strategy).lower()
            if requested_strategy in {"bayesiana", "bayesian", "optuna"} and effective_config.suggest_params is not None:
                effective_config = replace(effective_config, search_strategy="optuna")
            elif requested_strategy in {"grid", "manual", "grid_manual"}:
                effective_config = replace(effective_config, search_strategy="grid")

            if effective_config.search_strategy == "optuna":
                best_params, best_metrics = _optimize_with_optuna(
                    model_key,
                    X,
                    y,
                    preprocessor,
                    effective_config,
                    cv,
                    n_trials,
                )
            else:
                best_params, best_metrics = _optimize_with_grid(X, y, preprocessor, effective_config, cv)

            final_estimator = _fit_final_estimator(X, y, preprocessor, effective_config, best_params)
            result = ModelSearchResult(
                model_key=model_key,
                display_name=effective_config.display_name,
                best_params=best_params,
                rmse=best_metrics["rmse"],
                mae=best_metrics["mae"],
                r2=best_metrics["r2"],
                estimator=final_estimator,
                search_strategy=effective_config.search_strategy,
                duration_seconds=time.perf_counter() - started_at,
            )
            results.append(result)
            print(
                f"{config.display_name}: RMSE={result.rmse:.2f} | "
                f"MAE={result.mae:.2f} | R2={result.r2:.4f}"
            )
        except ImportError as exc:
            print(f"Pulando {config.display_name}: {exc}")

    if not results:
        raise RuntimeError("Nenhum modelo foi treinado. Verifique dependencias e registro de modelos.")

    ranking = pd.DataFrame(
        [
            {
                "model_key": result.model_key,
                "modelo": result.display_name,
                "rmse": result.rmse,
                "mae": result.mae,
                "r2": result.r2,
                "best_params": result.best_params,
                "search_strategy": result.search_strategy,
                "duration_seconds": result.duration_seconds,
            }
            for result in results
        ]
    ).sort_values("rmse", ascending=True, ignore_index=True)
    ranking.attrs["results"] = results

    print("\n=== Ranking final por RMSE ===")
    print(ranking[["modelo", "rmse", "mae", "r2"]].to_string(index=False))

    champion = min(results, key=lambda result: result.rmse)
    caminho = Path(caminho_modelo)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(champion.estimator, caminho)

    print(f"\nModelo campeao: {champion.display_name}")
    print(f"Modelo salvo em: {caminho}")
    return champion, ranking
