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

CREATE TABLE IF NOT EXISTS imoveis_tratados (
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

ALTER TABLE imoveis_tratados
    ADD COLUMN IF NOT EXISTS data_salvamento TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE imoveis_tratados
    ADD COLUMN IF NOT EXISTS id_lote INTEGER REFERENCES tb_lotes_ingestao(id_lote);
ALTER TABLE imoveis_tratados
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_imoveis_tratados_data_salvamento
    ON imoveis_tratados (data_salvamento);
CREATE INDEX IF NOT EXISTS idx_imoveis_tratados_id_lote
    ON imoveis_tratados (id_lote);
CREATE INDEX IF NOT EXISTS idx_imoveis_tratados_ativo_data
    ON imoveis_tratados (ativo, data_salvamento);

CREATE TABLE IF NOT EXISTS tb_experimentos_treino (
    id_experimento SERIAL PRIMARY KEY,
    data_inicio TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_fim TIMESTAMPTZ,
    tipo_busca TEXT NOT NULL,
    modelos_solicitados JSONB NOT NULL DEFAULT '[]'::jsonb,
    param_grids JSONB NOT NULL DEFAULT '{}'::jsonb,
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
    parametros_usados JSONB NOT NULL DEFAULT '{}'::jsonb,
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
    metricas_extras JSONB NOT NULL DEFAULT '{}'::jsonb
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
