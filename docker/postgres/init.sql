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
    data_salvamento TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE imoveis_tratados
    ADD COLUMN IF NOT EXISTS data_salvamento TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_imoveis_tratados_data_salvamento
    ON imoveis_tratados (data_salvamento);
