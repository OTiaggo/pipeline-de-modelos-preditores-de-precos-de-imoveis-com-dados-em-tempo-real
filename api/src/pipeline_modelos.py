from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pandas as pd

try:
    from .models.registry import MODEL_REGISTRY
    from .models.types import DEFAULT_N_TRIALS, ModelConfig, ModelSearchResult
    from .utils.training import treinar_modelos
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from models.registry import MODEL_REGISTRY
    from models.types import DEFAULT_N_TRIALS, ModelConfig, ModelSearchResult
    from utils.training import treinar_modelos


def treinar_e_salvar(
    X: pd.DataFrame,
    y: pd.Series,
    preprocessor: Any,
    caminho_modelo: str | Path,
) -> float:
    """Compatibility wrapper used by app.py: train, save champion, return R2."""

    champion, _ranking = treinar_modelos(
        X,
        y,
        preprocessor,
        caminho_modelo=caminho_modelo,
    )
    return champion.r2


def load_dataset(dataset_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(dataset_path)


def start(
    dataset_path: str | Path,
    *,
    target_column: str = "preco",
    model_path: str | Path = "artifacts/modelo_campeao.pkl",
    n_trials: int = DEFAULT_N_TRIALS,
) -> tuple[ModelSearchResult, pd.DataFrame]:
    try:
        from .pipeline_dados import MODEL_FEATURES, criar_pre_processador
    except ImportError:
        from pipeline_dados import MODEL_FEATURES, criar_pre_processador

    dataset = load_dataset(dataset_path)
    missing = [column for column in MODEL_FEATURES + [target_column] if column not in dataset.columns]
    if missing:
        raise ValueError(f"Dataset nao contem colunas obrigatorias: {missing}")

    X = dataset[MODEL_FEATURES]
    y = pd.to_numeric(dataset[target_column], errors="coerce")
    valid_mask = y.notna()
    return treinar_modelos(
        X.loc[valid_mask].reset_index(drop=True),
        y.loc[valid_mask].reset_index(drop=True),
        criar_pre_processador(),
        caminho_modelo=model_path,
        n_trials=n_trials,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Treina e seleciona o modelo campeao para precos de imoveis.")
    parser.add_argument("dataset_path", help="CSV tratado contendo as features de modelo e a coluna preco.")
    parser.add_argument("--model-path", default="artifacts/modelo_campeao.pkl", help="Destino do modelo campeao.")
    parser.add_argument("--n-trials", type=int, default=DEFAULT_N_TRIALS, help="Tentativas Optuna por modelo.")
    args = parser.parse_args()

    start(args.dataset_path, model_path=args.model_path, n_trials=args.n_trials)
