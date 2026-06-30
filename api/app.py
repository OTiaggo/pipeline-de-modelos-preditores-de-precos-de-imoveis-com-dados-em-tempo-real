from __future__ import annotations

import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.pipeline_dados import (
    BOOLEAN_FEATURES,
    MODEL_FEATURES,
    TARGET,
    criar_pre_processador,
    tratar_imoveis,
)
from src.models.types import DEFAULT_N_TRIALS
from src.models.registry import MODEL_REGISTRY
from src.pipeline_modelos import treinar_modelos

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor, execute_values
except ImportError:
    psycopg2 = None
    execute_values = None
    RealDictCursor = None
    Json = None


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@localhost:5432/dados_imobiliarios_fortaleza",
)
CAMINHO_MODELO = Path(os.getenv("CAMINHO_MODELO", "artifacts/modelo_campeao.pkl"))
ARTIFACTS_MODELOS_DIR = Path(os.getenv("ARTIFACTS_MODELOS_DIR", str(CAMINHO_MODELO.parent / "modelos")))
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
    "id_lote",
    "ativo",
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


class TrainRequest(BaseModel):
    modelos: list[str] | None = None
    tipo_busca: str = "bayesiana"
    n_trials: int = Field(default=DEFAULT_N_TRIALS, ge=1, le=200)
    param_grids: dict[str, dict[str, list[Any]]] = Field(default_factory=dict)


def _get_connection():
    if psycopg2 is None:
        raise RuntimeError("Dependencia ausente: instale psycopg2-binary para usar o Postgres.")
    return psycopg2.connect(DATABASE_URL)


def _ensure_schema() -> None:
    sql = f"""
    CREATE TABLE IF NOT EXISTS tb_lotes_ingestao (
        id_lote SERIAL PRIMARY KEY,
        nome_arquivo TEXT NOT NULL,
        data_upload TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        linhas_brutas INTEGER NOT NULL DEFAULT 0,
        linhas_tratadas INTEGER NOT NULL DEFAULT 0,
        linhas_salvas INTEGER NOT NULL DEFAULT 0,
        linhas_descartadas INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'processando',
        mensagem_erro TEXT
    );

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
        data_salvamento TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        id_lote INTEGER REFERENCES tb_lotes_ingestao(id_lote),
        ativo BOOLEAN NOT NULL DEFAULT TRUE
    );
    ALTER TABLE {TABELA_IMOVEIS}
        ADD COLUMN IF NOT EXISTS varanda_gourmet BOOLEAN;
    ALTER TABLE {TABELA_IMOVEIS}
        ADD COLUMN IF NOT EXISTS data_salvamento TIMESTAMPTZ NOT NULL DEFAULT NOW();
    ALTER TABLE {TABELA_IMOVEIS}
        ADD COLUMN IF NOT EXISTS id_lote INTEGER REFERENCES tb_lotes_ingestao(id_lote);
    ALTER TABLE {TABELA_IMOVEIS}
        ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;
    CREATE INDEX IF NOT EXISTS idx_imoveis_tratados_data_salvamento
        ON {TABELA_IMOVEIS} (data_salvamento);
    CREATE INDEX IF NOT EXISTS idx_imoveis_tratados_id_lote
        ON {TABELA_IMOVEIS} (id_lote);
    CREATE INDEX IF NOT EXISTS idx_imoveis_tratados_ativo_data
        ON {TABELA_IMOVEIS} (ativo, data_salvamento);

    CREATE TABLE IF NOT EXISTS tb_experimentos_treino (
        id_experimento SERIAL PRIMARY KEY,
        data_inicio TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        data_fim TIMESTAMPTZ,
        tipo_busca TEXT NOT NULL,
        modelos_solicitados JSONB NOT NULL DEFAULT '[]'::jsonb,
        param_grids JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        n_trials INTEGER NOT NULL DEFAULT 10,
        status TEXT NOT NULL DEFAULT 'pendente',
        amostras_treinamento INTEGER NOT NULL DEFAULT 0,
        janela_inicio TIMESTAMPTZ,
        janela_fim TIMESTAMPTZ,
        mensagem_erro TEXT
    );

    CREATE TABLE IF NOT EXISTS tb_modelos_treinados (
        id_modelo SERIAL PRIMARY KEY,
        id_experimento INTEGER NOT NULL REFERENCES tb_experimentos_treino(id_experimento),
        algoritmo TEXT NOT NULL,
        algoritmo_chave TEXT NOT NULL,
        parametros_usados JSONB NOT NULL DEFAULT '{{}}'::jsonb,
        caminho_artefato TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'concluido',
        is_campeao_experimento BOOLEAN NOT NULL DEFAULT FALSE,
        feature_importance JSONB,
        criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS tb_metricas_modelos (
        id_modelo INTEGER PRIMARY KEY REFERENCES tb_modelos_treinados(id_modelo),
        rmse DOUBLE PRECISION,
        mae DOUBLE PRECISION,
        r2 DOUBLE PRECISION,
        tempo_treino_segundos DOUBLE PRECISION,
        metricas_extras JSONB NOT NULL DEFAULT '{{}}'::jsonb
    );

    CREATE TABLE IF NOT EXISTS tb_modelo_ativo (
        singleton BOOLEAN PRIMARY KEY DEFAULT TRUE,
        id_modelo INTEGER REFERENCES tb_modelos_treinados(id_modelo),
        ativado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CHECK (singleton)
    );

    CREATE TABLE IF NOT EXISTS tb_logs_treinamento (
        id_log SERIAL PRIMARY KEY,
        id_experimento INTEGER NOT NULL REFERENCES tb_experimentos_treino(id_experimento),
        criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        nivel TEXT NOT NULL DEFAULT 'info',
        mensagem TEXT NOT NULL
    );
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


def _json_param(value: Any) -> Any:
    if Json is None:
        return json.dumps(value)
    return Json(value)


def _fetchall(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    _ensure_schema()
    with _get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


def _fetchone(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    rows = _fetchall(query, params)
    return rows[0] if rows else None


def criar_lote_ingestao(nome_arquivo: str, linhas_brutas: int) -> int:
    _ensure_schema()
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tb_lotes_ingestao (nome_arquivo, linhas_brutas, status)
                VALUES (%s, %s, 'processando')
                RETURNING id_lote
                """,
                (nome_arquivo, linhas_brutas),
            )
            return int(cursor.fetchone()[0])


def atualizar_lote_ingestao(
    id_lote: int,
    *,
    status: str,
    linhas_tratadas: int = 0,
    linhas_salvas: int = 0,
    linhas_descartadas: int = 0,
    mensagem_erro: str | None = None,
) -> None:
    _ensure_schema()
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE tb_lotes_ingestao
                SET status = %s,
                    linhas_tratadas = %s,
                    linhas_salvas = %s,
                    linhas_descartadas = %s,
                    mensagem_erro = %s
                WHERE id_lote = %s
                """,
                (status, linhas_tratadas, linhas_salvas, linhas_descartadas, mensagem_erro, id_lote),
            )


def salvar_dados_postgres(df: pd.DataFrame, id_lote: int | None = None) -> int:
    if df.empty:
        return 0
    if execute_values is None:
        raise RuntimeError("Dependencia ausente: instale psycopg2-binary para usar o Postgres.")

    _ensure_schema()
    df = df.copy()
    if id_lote is not None:
        df["id_lote"] = id_lote
    if "ativo" not in df.columns:
        df["ativo"] = True
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
          AND ativo = TRUE
    """
    with _get_connection() as conn:
        return pd.read_sql_query(query, conn)


def carregar_modelo_do_disco() -> None:
    global modelo_carregado
    active = None
    try:
        active = obter_modelo_ativo()
    except Exception:
        active = None
    caminho = Path(active["caminho_artefato"]) if active and active.get("caminho_artefato") else CAMINHO_MODELO
    if caminho.exists():
        modelo_carregado = joblib.load(caminho)


def listar_lotes_ingestao(limit: int = 50) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT id_lote, nome_arquivo, data_upload, linhas_brutas, linhas_tratadas,
               linhas_salvas, linhas_descartadas, status, mensagem_erro
        FROM tb_lotes_ingestao
        ORDER BY data_upload DESC
        LIMIT %s
        """,
        (limit,),
    )


def obter_status_dados() -> dict[str, Any]:
    resumo = _fetchone(
        f"""
        SELECT
            COUNT(*)::INTEGER AS total_imoveis_ativos,
            MAX(data_salvamento) AS ultima_atualizacao,
            AVG(preco)::DOUBLE PRECISION AS preco_medio_geral,
            AVG(preco_m2)::DOUBLE PRECISION AS preco_m2_medio
        FROM {TABELA_IMOVEIS}
        WHERE ativo = TRUE
        """
    ) or {}
    tipos = _fetchall(
        f"""
        SELECT tipo_imovel_padronizado AS tipo, COUNT(*)::INTEGER AS total
        FROM {TABELA_IMOVEIS}
        WHERE ativo = TRUE
        GROUP BY tipo_imovel_padronizado
        ORDER BY total DESC
        LIMIT 10
        """
    )
    bairros = _fetchall(
        f"""
        SELECT bairro, COUNT(*)::INTEGER AS total, AVG(preco)::DOUBLE PRECISION AS preco_medio
        FROM {TABELA_IMOVEIS}
        WHERE ativo = TRUE
        GROUP BY bairro
        ORDER BY total DESC
        LIMIT 10
        """
    )
    lotes = _fetchall(
        """
        SELECT data_upload::date AS data, SUM(linhas_salvas)::INTEGER AS linhas_salvas
        FROM tb_lotes_ingestao
        WHERE status = 'sucesso'
        GROUP BY data_upload::date
        ORDER BY data DESC
        LIMIT 12
        """
    )
    return {
        **resumo,
        "distribuicao_tipos": tipos,
        "top_bairros": bairros,
        "volume_por_lote": lotes,
    }


def rollback_lote(id_lote: int) -> dict[str, Any]:
    _ensure_schema()
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status FROM tb_lotes_ingestao WHERE id_lote = %s", (id_lote,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Lote nao encontrado.")
            cursor.execute(
                f"UPDATE {TABELA_IMOVEIS} SET ativo = FALSE WHERE id_lote = %s AND ativo = TRUE",
                (id_lote,),
            )
            registros_desativados = cursor.rowcount
            cursor.execute(
                """
                UPDATE tb_lotes_ingestao
                SET status = 'desativado',
                    mensagem_erro = NULL
                WHERE id_lote = %s
                """,
                (id_lote,),
            )
    return {"id_lote": id_lote, "status": "desativado", "registros_desativados": registros_desativados}


def validar_requisicao_treino(request: TrainRequest) -> list[str]:
    modelos = request.modelos or list(MODEL_REGISTRY)
    invalidos = [modelo for modelo in modelos if modelo not in MODEL_REGISTRY]
    if invalidos:
        raise HTTPException(status_code=400, detail=f"Modelos nao suportados: {invalidos}")
    for modelo, grid in request.param_grids.items():
        if modelo not in MODEL_REGISTRY:
            raise HTTPException(status_code=400, detail=f"Grid informado para modelo nao suportado: {modelo}")
        allowed = set((MODEL_REGISTRY[modelo].param_grid or {}).keys())
        allowed.update((MODEL_REGISTRY[modelo].suggest_params is not None and grid.keys()) or [])
        unknown = [key for key in grid if allowed and key not in allowed]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Hiperparametros nao suportados para {modelo}: {unknown}")
    return modelos


def criar_experimento_treino(request: TrainRequest, modelos: list[str]) -> int:
    _ensure_schema()
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tb_experimentos_treino
                    (tipo_busca, modelos_solicitados, param_grids, n_trials, status, janela_inicio, janela_fim)
                VALUES (%s, %s, %s, %s, 'pendente', NOW() - INTERVAL '1 year', NOW())
                RETURNING id_experimento
                """,
                (
                    request.tipo_busca,
                    _json_param(modelos),
                    _json_param(request.param_grids),
                    request.n_trials,
                ),
            )
            return int(cursor.fetchone()[0])


def registrar_log_treinamento(id_experimento: int, mensagem: str, nivel: str = "info") -> None:
    try:
        _ensure_schema()
        with _get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO tb_logs_treinamento (id_experimento, nivel, mensagem)
                    VALUES (%s, %s, %s)
                    """,
                    (id_experimento, nivel, mensagem),
                )
    except Exception:
        pass


def atualizar_experimento(
    id_experimento: int,
    *,
    status: str,
    amostras_treinamento: int | None = None,
    mensagem_erro: str | None = None,
    finalizar: bool = False,
) -> None:
    _ensure_schema()
    data_fim_sql = ", data_fim = NOW()" if finalizar else ""
    amostras_sql = ", amostras_treinamento = %s" if amostras_treinamento is not None else ""
    params: list[Any] = [status]
    if amostras_treinamento is not None:
        params.append(amostras_treinamento)
    params.extend([mensagem_erro, id_experimento])
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE tb_experimentos_treino
                SET status = %s{amostras_sql},
                    mensagem_erro = %s{data_fim_sql}
                WHERE id_experimento = %s
                """,
                tuple(params),
            )


def calcular_feature_importance(estimator: Any, feature_names: list[str]) -> list[dict[str, Any]]:
    regressor = estimator
    if hasattr(estimator, "named_steps"):
        regressor = estimator.named_steps.get("regressor", estimator)
    values = getattr(regressor, "feature_importances_", None)
    if values is None:
        coefs = getattr(regressor, "coef_", None)
        if coefs is not None:
            values = abs(pd.Series(coefs).to_numpy().ravel())
    if values is None:
        return []
    values = list(values)
    if len(values) != len(feature_names):
        feature_names = [f"feature_{index + 1}" for index in range(len(values))]
    ranking = sorted(
        ({"feature": name, "importance": float(value)} for name, value in zip(feature_names, values, strict=False)),
        key=lambda item: item["importance"],
        reverse=True,
    )
    return ranking[:20]


def registrar_modelo_treinado(
    id_experimento: int,
    result: Any,
    caminho_artefato: Path,
    *,
    is_campeao: bool,
    feature_importance: list[dict[str, Any]],
) -> int:
    _ensure_schema()
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tb_modelos_treinados
                    (id_experimento, algoritmo, algoritmo_chave, parametros_usados, caminho_artefato,
                     status, is_campeao_experimento, feature_importance)
                VALUES (%s, %s, %s, %s, %s, 'concluido', %s, %s)
                RETURNING id_modelo
                """,
                (
                    id_experimento,
                    result.display_name,
                    result.model_key,
                    _json_param(result.best_params),
                    str(caminho_artefato),
                    is_campeao,
                    _json_param(feature_importance),
                ),
            )
            id_modelo = int(cursor.fetchone()[0])
            cursor.execute(
                """
                INSERT INTO tb_metricas_modelos
                    (id_modelo, rmse, mae, r2, tempo_treino_segundos)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (id_modelo, result.rmse, result.mae, result.r2, result.duration_seconds),
            )
            return id_modelo


def ativar_modelo(id_modelo: int) -> dict[str, Any]:
    modelo = _fetchone(
        """
        SELECT mt.id_modelo, mt.caminho_artefato, mt.algoritmo, mm.rmse, mm.mae, mm.r2
        FROM tb_modelos_treinados mt
        LEFT JOIN tb_metricas_modelos mm ON mm.id_modelo = mt.id_modelo
        WHERE mt.id_modelo = %s AND mt.status = 'concluido'
        """,
        (id_modelo,),
    )
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo treinado nao encontrado.")
    if not Path(modelo["caminho_artefato"]).exists():
        raise HTTPException(status_code=409, detail="Artefato do modelo nao encontrado.")
    _ensure_schema()
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tb_modelo_ativo (singleton, id_modelo, ativado_em)
                VALUES (TRUE, %s, NOW())
                ON CONFLICT (singleton)
                DO UPDATE SET id_modelo = EXCLUDED.id_modelo, ativado_em = NOW()
                """,
                (id_modelo,),
            )
    global modelo_carregado
    modelo_carregado = joblib.load(modelo["caminho_artefato"])
    return modelo


def obter_modelo_ativo() -> dict[str, Any] | None:
    return _fetchone(
        """
        SELECT mt.id_modelo, mt.id_experimento, mt.algoritmo, mt.algoritmo_chave,
               mt.parametros_usados, mt.caminho_artefato, mt.feature_importance,
               ma.ativado_em, mm.rmse, mm.mae, mm.r2, mm.tempo_treino_segundos
        FROM tb_modelo_ativo ma
        JOIN tb_modelos_treinados mt ON mt.id_modelo = ma.id_modelo
        LEFT JOIN tb_metricas_modelos mm ON mm.id_modelo = mt.id_modelo
        WHERE ma.singleton = TRUE
        """
    )


def listar_experimentos(limit: int = 30) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT id_experimento, data_inicio, data_fim, tipo_busca, modelos_solicitados,
               n_trials, status, amostras_treinamento, mensagem_erro
        FROM tb_experimentos_treino
        ORDER BY data_inicio DESC
        LIMIT %s
        """,
        (limit,),
    )


def listar_leaderboard(limit: int = 100) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT mt.id_modelo, mt.id_experimento, mt.algoritmo, mt.algoritmo_chave,
               mt.parametros_usados, mt.caminho_artefato, mt.is_campeao_experimento,
               mt.criado_em, mm.rmse, mm.mae, mm.r2, mm.tempo_treino_segundos,
               (ma.id_modelo IS NOT NULL) AS ativo
        FROM tb_modelos_treinados mt
        LEFT JOIN tb_metricas_modelos mm ON mm.id_modelo = mt.id_modelo
        LEFT JOIN tb_modelo_ativo ma ON ma.id_modelo = mt.id_modelo
        ORDER BY mm.rmse ASC NULLS LAST, mt.criado_em DESC
        LIMIT %s
        """,
        (limit,),
    )


def obter_logs_experimento(id_experimento: int) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT id_log, criado_em, nivel, mensagem
        FROM tb_logs_treinamento
        WHERE id_experimento = %s
        ORDER BY id_log ASC
        """,
        (id_experimento,),
    )


def obter_experimento(id_experimento: int) -> dict[str, Any]:
    experimento = _fetchone(
        """
        SELECT id_experimento, data_inicio, data_fim, tipo_busca, modelos_solicitados,
               param_grids, n_trials, status, amostras_treinamento, mensagem_erro
        FROM tb_experimentos_treino
        WHERE id_experimento = %s
        """,
        (id_experimento,),
    )
    if not experimento:
        raise HTTPException(status_code=404, detail="Experimento nao encontrado.")
    modelos = _fetchall(
        """
        SELECT mt.id_modelo, mt.algoritmo, mt.algoritmo_chave, mt.is_campeao_experimento,
               mm.rmse, mm.mae, mm.r2, mm.tempo_treino_segundos
        FROM tb_modelos_treinados mt
        LEFT JOIN tb_metricas_modelos mm ON mm.id_modelo = mt.id_modelo
        WHERE mt.id_experimento = %s
        ORDER BY mm.rmse ASC NULLS LAST
        """,
        (id_experimento,),
    )
    experimento["modelos"] = modelos
    return experimento


def executar_treino_experimento(id_experimento: int, request: TrainRequest) -> None:
    modelos = request.modelos or list(MODEL_REGISTRY)
    registrar_log_treinamento(id_experimento, "Iniciando carregamento dos dados ativos do ultimo ano.")
    atualizar_experimento(id_experimento, status="executando")
    try:
        dados = carregar_dados_ultimo_ano()
        if dados.empty:
            raise ValueError("Nao ha dados ativos do ultimo ano para treinamento.")

        dados_modelo = dados.dropna(subset=MODEL_FEATURES + [TARGET]).copy()
        if dados_modelo.empty:
            raise ValueError("Dados do ultimo ano nao possuem features obrigatorias suficientes.")

        X = dados_modelo[MODEL_FEATURES]
        y = pd.to_numeric(dados_modelo[TARGET], errors="coerce")
        valid_mask = y.notna()
        amostras = int(valid_mask.sum())
        if amostras < 3:
            raise ValueError("Treinamento requer ao menos 3 amostras validas.")

        atualizar_experimento(id_experimento, status="executando", amostras_treinamento=amostras)
        registrar_log_treinamento(id_experimento, f"{amostras} amostras validas carregadas.")
        registrar_log_treinamento(id_experimento, f"Modelos solicitados: {', '.join(modelos)}.")

        experimento_dir = ARTIFACTS_MODELOS_DIR / str(id_experimento)
        experimento_dir.mkdir(parents=True, exist_ok=True)
        champion, ranking = treinar_modelos(
            X.loc[valid_mask].reset_index(drop=True),
            y.loc[valid_mask].reset_index(drop=True),
            criar_pre_processador(),
            caminho_modelo=experimento_dir / "_campeao_tmp.pkl",
            model_keys=modelos,
            search_strategy=request.tipo_busca,
            param_grids=request.param_grids,
            n_trials=request.n_trials,
        )
        results = ranking.attrs.get("results", [champion])
        id_modelo_campeao: int | None = None
        for result in results:
            is_campeao = result.model_key == champion.model_key
            artifact_path = experimento_dir / f"{result.model_key}.pkl"
            joblib.dump(result.estimator, artifact_path)
            feature_importance = calcular_feature_importance(result.estimator, MODEL_FEATURES)
            id_modelo = registrar_modelo_treinado(
                id_experimento,
                result,
                artifact_path,
                is_campeao=is_campeao,
                feature_importance=feature_importance,
            )
            registrar_log_treinamento(
                id_experimento,
                f"{result.display_name} concluido: RMSE={result.rmse:.2f}, MAE={result.mae:.2f}, R2={result.r2:.4f}.",
            )
            if is_campeao:
                id_modelo_campeao = id_modelo

        if id_modelo_campeao is None:
            raise RuntimeError("Campeao treinado nao foi persistido.")
        ativar_modelo(id_modelo_campeao)
        atualizar_experimento(id_experimento, status="concluido", amostras_treinamento=amostras, finalizar=True)
        registrar_log_treinamento(id_experimento, f"Modelo campeao ativado: {champion.display_name}.")
    except Exception as exc:
        atualizar_experimento(id_experimento, status="falha", mensagem_erro=str(exc), finalizar=True)
        registrar_log_treinamento(id_experimento, f"Falha no treinamento: {exc}", nivel="error")


def obter_drift_modelo() -> dict[str, Any]:
    ativo = obter_modelo_ativo()
    if not ativo:
        return {"status": "cinza", "motivo": "Nenhum modelo ativo.", "recomendacao": "Treine um modelo antes de avaliar drift."}
    resumo = _fetchone(
        f"""
        SELECT
            AVG(CASE WHEN data_salvamento >= NOW() - INTERVAL '30 days' THEN preco END)::DOUBLE PRECISION AS preco_recente,
            AVG(CASE WHEN data_salvamento < NOW() - INTERVAL '30 days' THEN preco END)::DOUBLE PRECISION AS preco_base,
            AVG(CASE WHEN data_salvamento >= NOW() - INTERVAL '30 days' THEN preco_m2 END)::DOUBLE PRECISION AS preco_m2_recente,
            AVG(CASE WHEN data_salvamento < NOW() - INTERVAL '30 days' THEN preco_m2 END)::DOUBLE PRECISION AS preco_m2_base,
            COUNT(CASE WHEN data_salvamento >= NOW() - INTERVAL '30 days' THEN 1 END)::INTEGER AS amostras_recentes
        FROM {TABELA_IMOVEIS}
        WHERE ativo = TRUE
        """
    ) or {}
    preco_base = resumo.get("preco_base") or 0
    preco_recente = resumo.get("preco_recente") or 0
    variacao = ((preco_recente - preco_base) / preco_base) if preco_base else 0
    abs_variacao = abs(variacao)
    if resumo.get("amostras_recentes", 0) < 20:
        status = "amarelo"
        motivo = "Poucas amostras recentes para avaliar o mercado com confianca."
    elif abs_variacao >= 0.2:
        status = "vermelho"
        motivo = "Mudanca forte no preco medio recente."
    elif abs_variacao >= 0.1:
        status = "amarelo"
        motivo = "Mudanca moderada no preco medio recente."
    else:
        status = "verde"
        motivo = "Precos recentes estao proximos da base historica ativa."
    return {
        "status": status,
        "motivo": motivo,
        "recomendacao": "Retreine o modelo." if status in {"amarelo", "vermelho"} else "Modelo saudavel no indicador atual.",
        "variacao_preco_medio": round(float(variacao), 4),
        **resumo,
    }


def explicar_predicao(features: dict[str, Any]) -> list[dict[str, Any]]:
    ativo = obter_modelo_ativo()
    importance = (ativo or {}).get("feature_importance") or []
    if isinstance(importance, str):
        try:
            importance = json.loads(importance)
        except json.JSONDecodeError:
            importance = []
    explanations = []
    for item in importance[:5]:
        feature = item.get("feature")
        if feature in features:
            explanations.append(
                {
                    "feature": feature,
                    "valor": features.get(feature),
                    "impacto": item.get("importance", 0),
                    "descricao": f"{feature} foi um dos fatores mais relevantes do modelo ativo.",
                }
            )
    if not explanations:
        for feature in ["bairro", "area_m2", "quartos", "vagas", "tipo_imovel_padronizado"]:
            explanations.append(
                {
                    "feature": feature,
                    "valor": features.get(feature),
                    "impacto": None,
                    "descricao": f"{feature} compoe a entrada usada pelo modelo ativo.",
                }
            )
    return explanations


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

    id_lote = criar_lote_ingestao(filename, len(dados_brutos))
    try:
        resultado = tratar_imoveis(dados_brutos)
        linhas_salvas = salvar_dados_postgres(resultado.dados, id_lote=id_lote)
        linhas_descartadas = max(int(len(dados_brutos)) - int(len(resultado.dados)), 0)
        atualizar_lote_ingestao(
            id_lote,
            status="sucesso",
            linhas_tratadas=int(len(resultado.dados)),
            linhas_salvas=int(linhas_salvas),
            linhas_descartadas=linhas_descartadas,
        )
    except Exception as exc:
        atualizar_lote_ingestao(id_lote, status="falha", mensagem_erro=str(exc))
        raise HTTPException(status_code=500, detail=f"Erro no tratamento/persistencia: {exc}") from exc

    return {
        "status": "sucesso",
        "id_lote": id_lote,
        "linhas_recebidas": int(len(dados_brutos)),
        "linhas_tratadas": int(len(resultado.dados)),
        "linhas_salvas": int(linhas_salvas),
        "resumo_filtros": resultado.resumo_filtros.to_dict(orient="records"),
    }


@app.get("/data/status")
def data_status() -> dict[str, Any]:
    try:
        return obter_status_dados()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar estado dos dados: {exc}") from exc


@app.get("/data/ingestions")
def data_ingestions() -> dict[str, Any]:
    try:
        return {"ingestions": listar_lotes_ingestao()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar historico de ingestoes: {exc}") from exc


@app.post("/data/ingestions/{id_lote}/rollback")
def data_rollback(id_lote: int) -> dict[str, Any]:
    try:
        return rollback_lote(id_lote)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao desfazer ingestao: {exc}") from exc


@app.post("/trainModels")
def train_models(background_tasks: BackgroundTasks, request: TrainRequest | None = None) -> dict[str, Any]:
    request = request or TrainRequest()
    try:
        modelos = validar_requisicao_treino(request)
        id_experimento = criar_experimento_treino(request, modelos)
        background_tasks.add_task(executar_treino_experimento, id_experimento, request)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar treinamento: {exc}") from exc

    return {
        "status": "pendente",
        "id_experimento": id_experimento,
        "modelos": modelos,
        "tipo_busca": request.tipo_busca,
    }


@app.get("/training/{id_experimento}")
def training_status(id_experimento: int) -> dict[str, Any]:
    return obter_experimento(id_experimento)


@app.get("/training/{id_experimento}/logs")
def training_logs(id_experimento: int) -> dict[str, Any]:
    return {"logs": obter_logs_experimento(id_experimento)}


@app.get("/models/history")
def models_history() -> dict[str, Any]:
    return {"experimentos": listar_experimentos()}


@app.get("/models/leaderboard")
def models_leaderboard() -> dict[str, Any]:
    return {"modelos": listar_leaderboard()}


@app.get("/models/active")
def models_active() -> dict[str, Any]:
    active = obter_modelo_ativo()
    if not active:
        return {"modelo_ativo": None}
    return {"modelo_ativo": active}


@app.post("/models/{id_modelo}/activate")
def models_activate(id_modelo: int) -> dict[str, Any]:
    return {"modelo_ativo": ativar_modelo(id_modelo)}


@app.get("/models/{id_modelo}/feature-importance")
def model_feature_importance(id_modelo: int) -> dict[str, Any]:
    row = _fetchone("SELECT id_modelo, feature_importance FROM tb_modelos_treinados WHERE id_modelo = %s", (id_modelo,))
    if not row:
        raise HTTPException(status_code=404, detail="Modelo nao encontrado.")
    return {"id_modelo": id_modelo, "feature_importance": row.get("feature_importance") or []}


@app.get("/model-health/drift")
def model_health_drift() -> dict[str, Any]:
    return obter_drift_modelo()


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
        "explicacao": explicar_predicao(dados),
    }
