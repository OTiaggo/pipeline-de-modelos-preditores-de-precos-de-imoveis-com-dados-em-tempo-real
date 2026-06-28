from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET = "preco"

NUMERIC_FEATURES = [
    "area_m2",
    "quartos",
    "banheiros",
    "suites",
    "andar",
    "vagas",
]

BOOLEAN_FEATURES = [
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
]

CATEGORICAL_FEATURES = [
    "bairro",
    "tipo_imovel_padronizado",
]

MODEL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES + BOOLEAN_FEATURES

MUNICIPIOS_RMF = [
    "Aquiraz",
    "Cascavel",
    "Caucaia",
    "Chorozinho",
    "Eusebio",
    "Fortaleza",
    "Guaiuba",
    "Horizonte",
    "Itaitinga",
    "Maracanau",
    "Maranguape",
    "Pacajus",
    "Pacatuba",
    "Paracuru",
    "Paraipaba",
    "Pindoretama",
    "Sao Goncalo do Amarante",
    "Sao Luis do Curu",
    "Trairi",
]

MUNICIPIOS_NORM = {m.lower(): m for m in MUNICIPIOS_RMF}
MUNICIPIOS_NORM["sgda"] = "Sao Goncalo do Amarante"

NAO_RESIDENCIAL = {
    "RESIDENTIAL_ALLOTMENT_LAND",
    "COMMERCIAL_ALLOTMENT_LAND",
    "ALLOTMENT_LAND",
    "COMMERCIAL_PROPERTY",
    "COMMERCIAL_BUILDING",
    "FARM",
    "RETAIL_CENTER",
    "OFFICE",
    "BUSINESS",
}

MAPA_TIPO_IMOVEL = {
    "Venda - apartamento padrao": "apartamento_padrao",
    "APARTMENT": "apartamento_padrao",
    "Apartamento": "apartamento_padrao",
    "Venda - apartamento cobertura": "cobertura",
    "PENTHOUSE": "cobertura",
    "Venda - apartamento duplex/triplex": "duplex_triplex",
    "DUPLEX": "duplex_triplex",
    "Venda - apartamento kitchenette": "kitchenette_studio",
    "Venda - loft/studio": "kitchenette_studio",
    "STUDIO": "kitchenette_studio",
    "FLAT": "kitchenette_studio",
    "CONDOMINIUM": "apartamento_padrao",
    "Venda - casa em rua publica": "casa_padrao",
    "HOME": "casa_padrao",
    "Casa": "casa_padrao",
    "Venda - casa em condominio fechado": "casa_condominio",
    "Venda - casa em vila": "casa_padrao",
    "TWO_STORY_HOUSE": "casa_padrao",
    "SINGLE_STOREY_HOUSE": "casa_padrao",
    "RESIDENTIAL_BUILDING": "casa_padrao",
    "BUILDING": "casa_padrao",
}

BAIRRO_CANONICO = {
    "sapiranga / coite": "Sapiranga-Coite",
    "sapiranga-coite": "Sapiranga-Coite",
    "lagoa sapiranga coite": "Sapiranga-Coite",
    "sapiranga coite": "Sapiranga-Coite",
    "dionisio torres": "Dionisio Torres",
    "manoel dias branco": "Manuel Dias Branco",
    "manuel dias branco": "Manuel Dias Branco",
    "jose de alencar": "Jose de Alencar",
    "agua fria": "Agua Fria",
    "boa vista-castelao": "Boa Vista/Castelao",
    "boa vista castelao": "Boa Vista/Castelao",
}

REFERENCIAS_GEO = {
    "mar": (-3.7178, -38.4977),
    "meireles": (-3.7299, -38.4905),
    "aldeota": (-3.7340, -38.4960),
    "centro": (-3.7319, -38.5267),
}

RENOMEACAO_FINAL = {
    "apartamento_ou_casa": "tipo",
    "cidade_validada": "cidade",
    "bairro_normalizado": "bairro",
    "numero": "numero_endereco",
    "endereco": "endereco",
    "metragem": "area_m2",
    "quartos": "quartos",
    "banheiros_validado": "banheiros",
    "suites_validado": "suites",
    "andar": "andar",
    "vagas_validado": "vagas",
    "preco_anuncio": "preco",
    "preco_m2": "preco_m2",
    "latitude": "latitude",
    "longitude": "longitude",
    "tem_portaria_24h": "portaria",
    "tem_vista_pro_mar": "vista_mar",
    "tem_condominio_fechado": "condominio_fechado",
    "tem_piscina": "piscina",
    "tem_deck": "deck",
    "tem_varanda_gourmet": "varanda_gourmet",
    "tem_varanda": "varanda",
    "tem_academia": "academia",
    "tem_salao_festas": "salao_festa",
    "tem_salao_jogos": "salao_jogos",
    "tem_quadra_campo": "quadra_campo",
    "estado": "estado",
}

COLUNAS_EXTRA_FINAIS = [
    "listing_id",
    "titulo",
    "tipo_imovel_padronizado",
    "rua",
    "tem_geolocalizacao",
    "tem_endereco_estruturado",
    "andar_informado",
    "distancia_mar",
    "distancia_meireles",
    "distancia_aldeota",
    "distancia_centro",
    "fonte",
    "anuncio_criado",
    "corretora",
    "url",
    "data_salvamento",
]


@dataclass(frozen=True)
class ResultadoTratamento:
    dados: pd.DataFrame
    resumo_filtros: pd.DataFrame


def _strip_accents(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )


def _strip_key(value: object) -> str:
    if pd.isna(value):
        return ""
    text = _strip_accents(str(value)).lower().strip()
    return re.sub(r"\s+", " ", text)


def _coalesce_column(df: pd.DataFrame, target: str, aliases: Sequence[str]) -> None:
    if target not in df.columns:
        df[target] = np.nan

    for alias in aliases:
        if alias in df.columns:
            df[target] = df[target].combine_first(df[alias])


def _coerce_bool(series: pd.Series, default: bool = False) -> pd.Series:
    if series.empty:
        return series.astype(bool)

    truthy = {"true", "1", "sim", "s", "yes", "y", "t"}
    falsy = {"false", "0", "nao", "não", "n", "no", "f", ""}

    def parse(value: object) -> bool:
        if pd.isna(value):
            return default
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        if isinstance(value, (int, float, np.integer, np.floating)):
            return bool(value)
        key = _strip_key(value)
        if key in truthy:
            return True
        if key in falsy:
            return False
        return default

    return series.map(parse).astype(bool)


def _haversine_km(lat1: object, lon1: object, lat2: float, lon2: float) -> float:
    if pd.isna(lat1) or pd.isna(lon1):
        return np.nan

    radius = 6371.0
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return 2 * radius * atan2(sqrt(a), sqrt(1 - a))


def _detectar_cidade_real(texto_norm: str, cidade_estrutural: object) -> object:
    for chave, nome_oficial in MUNICIPIOS_NORM.items():
        if chave and re.search(r"\b" + re.escape(chave) + r"\b", texto_norm):
            return nome_oficial

    cidade_norm = _strip_key(cidade_estrutural)
    if cidade_norm in MUNICIPIOS_NORM:
        return MUNICIPIOS_NORM[cidade_norm]
    return cidade_estrutural if isinstance(cidade_estrutural, str) else np.nan


def _padronizar_tipo(tipo_imovel: object, fallback: object) -> str:
    if tipo_imovel in NAO_RESIDENCIAL:
        return "nao_residencial"
    if tipo_imovel in MAPA_TIPO_IMOVEL:
        return MAPA_TIPO_IMOVEL[tipo_imovel]

    tipo_norm = _strip_key(tipo_imovel)
    for chave, valor in MAPA_TIPO_IMOVEL.items():
        if _strip_key(chave) == tipo_norm:
            return valor

    if tipo_norm in {"apartamento", "apartment"}:
        return "apartamento_padrao"
    if tipo_norm in {"casa", "home"}:
        return "casa_padrao"

    fallback_norm = _strip_key(fallback)
    return "casa_padrao" if fallback_norm == "casa" else "apartamento_padrao"


def _normalizar_bairro(valor: object) -> object:
    if not isinstance(valor, str) or not valor.strip():
        return np.nan

    chave = _strip_key(valor)
    return BAIRRO_CANONICO.get(chave, valor.strip())


def _normalizar_schema_entrada(df: pd.DataFrame) -> pd.DataFrame:
    dados = df.copy()

    aliases = {
        "preco_anuncio": ["preco", "Price", "price"],
        "metragem": ["area_m2", "Area", "area"],
        "quartos": ["Bedrooms", "bedrooms"],
        "banheiros": ["Bathrooms", "bathrooms"],
        "estacionamentos": ["vagas", "Parking_Spaces", "parking_spaces"],
        "bairro": ["Neighborhood", "neighborhood"],
        "latitude": ["Latitude"],
        "longitude": ["Longitude"],
        "anuncio_criado": ["created_date", "Created_Date"],
    }
    for target, column_aliases in aliases.items():
        _coalesce_column(dados, target, column_aliases)

    if "apartamento_ou_casa" not in dados.columns:
        tipo_imovel_base = dados["tipo_imovel"] if "tipo_imovel" in dados.columns else pd.Series(index=dados.index, dtype="object")
        dados["apartamento_ou_casa"] = np.where(
            tipo_imovel_base.astype(str).str.contains("casa|home", case=False, na=False),
            "casa",
            "apartamento",
        )

    if "tipo_imovel" not in dados.columns:
        dados["tipo_imovel"] = dados["apartamento_ou_casa"]

    if "cidade" not in dados.columns:
        dados["cidade"] = "Fortaleza"

    if "estado" not in dados.columns:
        dados["estado"] = "CE"

    amenity_aliases = {
        "tem_portaria_24h": ["portaria", "portaria_24h_normalizado"],
        "tem_vista_pro_mar": ["vista_mar", "vista_mar_normalizado"],
        "tem_condominio_fechado": ["condominio_fechado", "condominio_fechado_normalizado"],
        "tem_piscina": ["piscina", "piscina_normalizado"],
        "tem_deck": ["deck", "deck_normalizado"],
        "tem_varanda_gourmet": ["varanda_gourmet", "varanda_gourmet_normalizado"],
        "tem_varanda": ["varanda", "varanda_normalizado"],
        "tem_academia": ["academia", "academia_normalizado"],
        "tem_salao_festas": ["salao_festa", "salao_festas_normalizado"],
        "tem_salao_jogos": ["salao_jogos", "salao_jogos_normalizado"],
        "tem_quadra_campo": ["quadra_campo", "quadra_normalizado"],
    }
    for target, column_aliases in amenity_aliases.items():
        _coalesce_column(dados, target, column_aliases)
        dados[target] = _coerce_bool(dados[target])

    for column in ["preco_anuncio", "metragem", "quartos", "banheiros", "suites", "andar", "estacionamentos", "latitude", "longitude"]:
        if column not in dados.columns:
            dados[column] = np.nan
        dados[column] = pd.to_numeric(dados[column], errors="coerce")

    for column in ["titulo", "descricao", "endereco", "numero", "rua", "corretora", "url", "listing_id", "fonte"]:
        if column not in dados.columns:
            dados[column] = np.nan

    return dados


def carregar_fontes_csv(arquivos_por_fonte: Mapping[str, str | Path]) -> pd.DataFrame:
    frames = []
    for fonte, caminho in arquivos_por_fonte.items():
        frame = pd.read_csv(caminho)
        frame["fonte"] = fonte
        frames.append(frame)

    if not frames:
        raise ValueError("Informe ao menos um CSV para carregar.")
    return pd.concat(frames, ignore_index=True)


def tratar_imoveis(
    dados_brutos: pd.DataFrame,
    *,
    manter_apenas_features_modelo: bool = False,
    data_salvamento: pd.Timestamp | None = None,
) -> ResultadoTratamento:
    df = _normalizar_schema_entrada(dados_brutos)
    data_salvamento = data_salvamento or pd.Timestamp.utcnow().normalize()

    if "nota_media" in df.columns:
        df = df.drop(columns=["nota_media"])

    texto_busca = (
        df["titulo"].fillna("").astype(str)
        + " || "
        + df["descricao"].fillna("").astype(str)
        + " || "
        + df["endereco"].fillna("").astype(str)
    ).map(_strip_key)
    df["cidade_validada"] = [
        _detectar_cidade_real(texto, cidade)
        for texto, cidade in zip(texto_busca, df["cidade"], strict=False)
    ]

    df["tipo_imovel_padronizado"] = [
        _padronizar_tipo(tipo, fallback)
        for tipo, fallback in zip(df["tipo_imovel"], df["apartamento_ou_casa"], strict=False)
    ]
    df["bairro_normalizado"] = df["bairro"].map(_normalizar_bairro)

    df["tem_geolocalizacao"] = df["latitude"].notna() & df["longitude"].notna()
    df["tem_endereco_estruturado"] = df["endereco"].notna()
    df["andar_informado"] = df["andar"].notna()

    for nome, (lat_ref, lon_ref) in REFERENCIAS_GEO.items():
        df[f"distancia_{nome}"] = [
            _haversine_km(lat, lon, lat_ref, lon_ref)
            for lat, lon in zip(df["latitude"], df["longitude"], strict=False)
        ]

    df["suites_validado"] = np.minimum(df["suites"], df["quartos"])
    df["banheiros_validado"] = np.maximum(df["banheiros"], df["suites_validado"].fillna(0))
    df["vagas_validado"] = df["estacionamentos"].clip(lower=0, upper=12)
    df["preco_m2"] = np.where(
        (df["metragem"] > 0) & df["preco_anuncio"].notna(),
        df["preco_anuncio"] / df["metragem"],
        np.nan,
    )
    df["data_salvamento"] = pd.to_datetime(data_salvamento)

    escopo_residencial = ~df["tipo_imovel"].isin(NAO_RESIDENCIAL)
    lim_metragem = df.loc[escopo_residencial, "metragem"].quantile(0.995)
    lim_preco = df.loc[escopo_residencial, "preco_anuncio"].quantile(0.995)
    if pd.isna(lim_metragem):
        lim_metragem = np.inf
    if pd.isna(lim_preco):
        lim_preco = np.inf

    etapas = [("Inicial", len(df))]

    if "listing_id" in df.columns and df["listing_id"].notna().any():
        df = df.drop_duplicates(subset=["listing_id"], keep="first")
    etapas.append(("Dedup por listing_id", len(df)))

    chave_dup = (
        df["endereco"].astype(str).str.lower().str.strip()
        + "|"
        + df["preco_anuncio"].astype(str)
        + "|"
        + df["metragem"].astype(str)
    )
    df = df[~(chave_dup.duplicated(keep="first") & df["endereco"].notna())]
    etapas.append(("Dedup por conteudo", len(df)))

    df = df[df["cidade_validada"].isin(MUNICIPIOS_RMF)]
    etapas.append(("Filtro RMF", len(df)))

    df = df[~df["tipo_imovel"].isin(NAO_RESIDENCIAL)]
    etapas.append(("Escopo residencial", len(df)))

    df = df[(df["preco_anuncio"].isna()) | (df["preco_anuncio"] >= 10_000)]
    df = df[(df["preco_anuncio"].isna()) | (df["preco_anuncio"] <= lim_preco)]
    df = df[(df["metragem"].isna()) | (df["metragem"] <= lim_metragem)]
    df = df[(df["quartos"].isna()) | (df["quartos"] <= 15)]
    df = df[(df["banheiros_validado"].isna()) | (df["banheiros_validado"] <= 15)]
    df = df[(df["andar"].isna()) | (df["andar"] <= 60)]
    etapas.append(("Cortes de outliers", len(df)))

    df = df.dropna(subset=["preco_anuncio", "metragem"])
    etapas.append(("Sem preco/metragem removidos", len(df)))

    colunas_finais = [c for c in RENOMEACAO_FINAL if c in df.columns] + [
        c for c in COLUNAS_EXTRA_FINAIS if c in df.columns
    ]
    df_final = df[colunas_finais].rename(columns=RENOMEACAO_FINAL)

    for feature in MODEL_FEATURES:
        if feature in BOOLEAN_FEATURES and feature not in df_final.columns:
            df_final[feature] = False
        elif feature not in df_final.columns:
            df_final[feature] = np.nan

    colunas_essenciais = ["bairro", "area_m2", TARGET, "vagas", "quartos", "banheiros", "suites", "andar"]
    df_final = df_final.dropna(subset=[c for c in colunas_essenciais if c in df_final.columns])
    df_final = df_final[(df_final[TARGET] > 0) & (df_final["area_m2"] > 0)]
    etapas.append(("Features essenciais validas", len(df_final)))

    for column in BOOLEAN_FEATURES:
        df_final[column] = _coerce_bool(df_final[column])

    if manter_apenas_features_modelo:
        df_final = df_final[MODEL_FEATURES + [TARGET, "data_salvamento"]]

    resumo = pd.DataFrame(etapas, columns=["etapa", "registros_restantes"])
    resumo["removidos_na_etapa"] = -resumo["registros_restantes"].diff().fillna(0).astype(int)
    resumo.loc[0, "removidos_na_etapa"] = 0

    return ResultadoTratamento(dados=df_final.reset_index(drop=True), resumo_filtros=resumo)


def salvar_dados_tratados(dados: pd.DataFrame, caminho_saida: str | Path) -> None:
    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados.to_csv(caminho, index=False)


def preparar_dados_para_treino(
    df_novo: pd.DataFrame,
    caminho_historico: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    resultado = tratar_imoveis(df_novo, manter_apenas_features_modelo=True)
    dados_tratados = resultado.dados

    if dados_tratados.empty:
        raise ValueError("Nenhum registro valido restou apos o tratamento dos dados.")

    if caminho_historico:
        caminho = Path(caminho_historico)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        if caminho.exists():
            historico = pd.read_csv(caminho)
            colunas_compativeis = [c for c in dados_tratados.columns if c in historico.columns]
            if set(MODEL_FEATURES + [TARGET]).issubset(colunas_compativeis):
                historico = historico[colunas_compativeis]
                dados_tratados = pd.concat([historico, dados_tratados[colunas_compativeis]], ignore_index=True)
        dados_tratados = dados_tratados.drop_duplicates()
        salvar_dados_tratados(dados_tratados, caminho)

    dados_modelo = dados_tratados.dropna(subset=MODEL_FEATURES + [TARGET])
    if dados_modelo.empty:
        raise ValueError("Nao ha dados suficientes com todas as features obrigatorias para treino.")

    X = dados_modelo[MODEL_FEATURES].copy()
    y = pd.to_numeric(dados_modelo[TARGET], errors="coerce")
    mascara_valida = y.notna()
    return X.loc[mascara_valida].reset_index(drop=True), y.loc[mascara_valida].reset_index(drop=True)


def _one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def criar_pre_processador() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", _one_hot_encoder()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
            ("boolean", "passthrough", BOOLEAN_FEATURES),
        ],
        remainder="drop",
    )


def executar_pipeline_csv(
    entrada: str | Path | Mapping[str, str | Path],
    saida: str | Path = "dados_tratados/imoveis_tratado.csv",
) -> ResultadoTratamento:
    if isinstance(entrada, Mapping):
        dados_brutos = carregar_fontes_csv(entrada)
    else:
        dados_brutos = pd.read_csv(entrada)

    resultado = tratar_imoveis(dados_brutos)
    salvar_dados_tratados(resultado.dados, saida)
    return resultado
