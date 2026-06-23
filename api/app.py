from __future__ import annotations

import io
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.pipeline_dados import (
    BOOLEAN_FEATURES,
    MODEL_FEATURES,
    TARGET,
    criar_pre_processador,
    tratar_imoveis,
)
from src.pipeline_modelos import treinar_modelos

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None
    execute_values = None


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@localhost:5432/dados_imobiliarios_fortaleza",
)
CAMINHO_MODELO = Path(os.getenv("CAMINHO_MODELO", "artifacts/modelo_campeao.pkl"))
TABELA_IMOVEIS = "imoveis_tratados"

DB_COLUMNS = [
    "tipo",
    "cidade",
    "bairro",
    "area_m2",
    "quartos",
    "banheiros",
    "suites",
    "andar",
    "vagas",
    "preco",
    "preco_m2",
    "portaria",
    "vista_mar",
    "condominio_fechado",
    "piscina",
    "deck",
    "varanda_gourmet",
    "varanda",
    "academia",
    "salao_festa",
    "salao_jogos",
    "quadra_campo",
    "estado",
    "tipo_imovel_padronizado",
    "andar_informado",
    "data_salvamento",
]



@asynccontextmanager
async def lifespan(_app: FastAPI):
    carregar_modelo_do_disco()
    yield


app = FastAPI(
    title="API Predicao de Precos de Imoveis - Fortaleza",
    version="1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

modelo_carregado: Any | None = None


class ImovelInput(BaseModel):
    bairro: str
    area_m2: float = Field(gt=0)
    quartos: int = Field(ge=0)
    banheiros: int = Field(ge=0)
    suites: int = Field(ge=0)
    andar: int = Field(ge=0)
    vagas: int = Field(ge=0)
    tipo_imovel_padronizado: str = "apartamento_padrao"
    portaria: bool = False
    vista_mar: bool = False
    condominio_fechado: bool = False
    piscina: bool = False
    deck: bool = False
    varanda_gourmet: bool = False
    varanda: bool = False
    academia: bool = False
    salao_festa: bool = False
    salao_jogos: bool = False
    quadra_campo: bool = False


def _get_connection():
    if psycopg2 is None:
        raise RuntimeError("Dependencia ausente: instale psycopg2-binary para usar o Postgres.")
    return psycopg2.connect(DATABASE_URL)


def _ensure_schema() -> None:
    sql = f"""
    CREATE TABLE IF NOT EXISTS {TABELA_IMOVEIS} (
        tipo TEXT,
        cidade TEXT,
        bairro TEXT,
        area_m2 NUMERIC(12, 2),
        quartos INTEGER,
        banheiros INTEGER,
        suites INTEGER,
        andar INTEGER,
        vagas INTEGER,
        preco NUMERIC(14, 2),
        preco_m2 NUMERIC(14, 2),
        portaria BOOLEAN,
        vista_mar BOOLEAN,
        condominio_fechado BOOLEAN,
        piscina BOOLEAN,
        deck BOOLEAN,
        varanda_gourmet BOOLEAN,
        varanda BOOLEAN,
        academia BOOLEAN,
        salao_festa BOOLEAN,
        salao_jogos BOOLEAN,
        quadra_campo BOOLEAN,
        estado TEXT,
        tipo_imovel_padronizado TEXT,
        andar_informado BOOLEAN,
        data_salvamento TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    ALTER TABLE {TABELA_IMOVEIS}
        ADD COLUMN IF NOT EXISTS data_salvamento TIMESTAMPTZ NOT NULL DEFAULT NOW();
    CREATE INDEX IF NOT EXISTS idx_imoveis_tratados_data_salvamento
        ON {TABELA_IMOVEIS} (data_salvamento);
    """
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)


def _records_for_insert(df: pd.DataFrame) -> list[tuple[Any, ...]]:
    dados = df.copy()
    if "data_salvamento" not in dados.columns:
        dados["data_salvamento"] = pd.Timestamp.utcnow()

    for column in DB_COLUMNS:
        if column not in dados.columns:
            dados[column] = None

    dados = dados[DB_COLUMNS].replace({pd.NaT: None})
    dados = dados.where(pd.notna(dados), None)
    return [tuple(_to_python_value(value) for value in row) for row in dados.itertuples(index=False, name=None)]


def _to_python_value(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()
    return value


def salvar_dados_postgres(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    if execute_values is None:
        raise RuntimeError("Dependencia ausente: instale psycopg2-binary para usar o Postgres.")

    _ensure_schema()
    columns_sql = ", ".join(DB_COLUMNS)
    insert_sql = f"INSERT INTO {TABELA_IMOVEIS} ({columns_sql}) VALUES %s"
    records = _records_for_insert(df)
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            execute_values(cursor, insert_sql, records)
    return len(records)


def carregar_dados_ultimo_ano() -> pd.DataFrame:
    _ensure_schema()
    query = f"""
        SELECT {", ".join(DB_COLUMNS)}
        FROM {TABELA_IMOVEIS}
        WHERE data_salvamento >= NOW() - INTERVAL '1 year'
    """
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn)


def carregar_modelo_do_disco() -> None:
    global modelo_carregado
    if CAMINHO_MODELO.exists():
        modelo_carregado = joblib.load(CAMINHO_MODELO)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/insertData")
async def insert_data(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo CSV.")

    contents = await file.read()
    try:
        dados_brutos = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erro ao ler CSV: {exc}") from exc

    try:
        resultado = tratar_imoveis(dados_brutos)
        linhas_salvas = salvar_dados_postgres(resultado.dados)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no tratamento/persistencia: {exc}") from exc

    return {
        "status": "sucesso",
        "linhas_recebidas": int(len(dados_brutos)),
        "linhas_tratadas": int(len(resultado.dados)),
        "linhas_salvas": int(linhas_salvas),
        "resumo_filtros": resultado.resumo_filtros.to_dict(orient="records"),
    }


@app.post("/trainModels")
def train_models() -> dict[str, Any]:
    global modelo_carregado

    try:
        dados = carregar_dados_ultimo_ano()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar dados do Postgres: {exc}") from exc

    if dados.empty:
        raise HTTPException(status_code=400, detail="Nao ha dados do ultimo ano para treinamento.")

    dados_modelo = dados.dropna(subset=MODEL_FEATURES + [TARGET]).copy()
    if dados_modelo.empty:
        raise HTTPException(status_code=400, detail="Dados do ultimo ano nao possuem features obrigatorias suficientes.")

    X = dados_modelo[MODEL_FEATURES]
    y = pd.to_numeric(dados_modelo[TARGET], errors="coerce")
    valid_mask = y.notna()

    try:
        champion, ranking = treinar_modelos(
            X.loc[valid_mask].reset_index(drop=True),
            y.loc[valid_mask].reset_index(drop=True),
            criar_pre_processador(),
            caminho_modelo=CAMINHO_MODELO,
        )
        modelo_carregado = joblib.load(CAMINHO_MODELO)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no treinamento: {exc}") from exc

    return {
        "status": "sucesso",
        "amostras_treinamento": int(valid_mask.sum()),
        "modelo_campeao": champion.display_name,
        "rmse": champion.rmse,
        "mae": champion.mae,
        "r2": champion.r2,
        "ranking": ranking.to_dict(orient="records"),
    }


@app.post("/predict")
def predict(features: ImovelInput) -> dict[str, Any]:
    if modelo_carregado is None:
        raise HTTPException(status_code=503, detail="Modelo indisponivel. Execute /trainModels primeiro.")

    try:
        dados = features.model_dump()
    except AttributeError:
        dados = features.dict()
    for column in BOOLEAN_FEATURES:
        dados.setdefault(column, False)

    df_input = pd.DataFrame([dados])[MODEL_FEATURES]
    try:
        predicao = float(modelo_carregado.predict(df_input)[0])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro na predicao: {exc}") from exc

    return {
        "preco_estimado": round(predicao, 2),
        "bairro": features.bairro,
        "tipo_imovel_padronizado": features.tipo_imovel_padronizado,
    }
