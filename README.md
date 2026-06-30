# Plataforma de Predição de Preços de Imóveis em Fortaleza

Projeto final da disciplina **Aprendizagem de Máquina - 2026.1**, orientado pelo professor César Lincoln Cavalcante Mattos. O trabalho atende à proposta de desenvolver, em grupo, uma solução com dados reais, preparação criteriosa dos dados, comparação entre múltiplos modelos de aprendizagem de máquina e entrega das implementações junto ao artigo.

Este repositório contém uma plataforma completa para estimar preços de imóveis residenciais em Fortaleza/CE a partir de dados coletados por web scraping. O sistema integra pipeline de dados, pipeline de modelos, API, banco PostgreSQL e interface web para ingestão de dados, retreinamento e predição.

## Objetivo

Construir um sistema de regressão para predizer o valor de venda de imóveis com base em características estruturais, localização e amenidades. A motivação é apoiar análises do mercado imobiliário usando dados reais e atualizados, mantendo o modelo alinhado ao comportamento recente de preços.

O sistema permite:

- Inserir novos dados brutos extraídos por scraping.
- Tratar, padronizar e persistir os dados em PostgreSQL.
- Treinar e comparar diferentes modelos de regressão.
- Selecionar automaticamente o melhor modelo com base em métricas de desempenho.
- Predizer o preço de um imóvel informado pelo usuário.
- Retreinar o modelo com dados recentes, considerando apenas registros do último ano.

## Relação com as instruções do trabalho

O PDF do projeto final solicita um trabalho de aprendizagem de máquina com dados reais, fundamentação, metodologia, experimentos, comparação de modelos e entrega do código. Este repositório se encaixa nesse escopo da seguinte forma:

| Exigência do trabalho | Como aparece no projeto |
| --- | --- |
| Uso de dados reais | Dados de imóveis obtidos por scraping de portais imobiliários. |
| Problema de aprendizagem de máquina | Regressão para predição de preço (`preco`). |
| Preparação criteriosa dos dados | Pipeline de limpeza, padronização, filtros, deduplicação e tratamento de outliers. |
| Mais de um modelo | XGBoost, LightGBM, CatBoost, Random Forest, Ridge, Lasso, SVR e MLP. |
| Comparação de desempenho | Ranking por RMSE, com MAE e R² retornados pela API. |
| Implementação entregue | Código da API, pipelines, scraping, frontend, Docker e testes. |
| Discussão de resultados | Artefatos e rankings salvos em `modelagem/artifacts_modelagem/`. |

## Features usadas no modelo

As variáveis preditoras seguem o escopo definido para o trabalho:

- `bairro`
- `area_m2`
- `quartos`
- `banheiros`
- `suites`
- `andar`
- `vagas`
- `portaria`
- `vista_mar`
- `condominio_fechado`
- `piscina`
- `deck`
- `varanda_gourmet`
- `varanda`
- `academia`
- `salao_festa`
- `salao_jogos`
- `quadra_campo`
- `tipo_imovel_padronizado`

Variável alvo:

- `preco`

## Arquitetura

```mermaid
flowchart LR
    Scraping[Web scraping] --> CSV[Dados brutos CSV]
    CSV --> API[FastAPI]
    API --> DataPipeline[Pipeline de dados]
    DataPipeline --> Postgres[(PostgreSQL)]
    Postgres --> ModelPipeline[Pipeline de modelos]
    ModelPipeline --> Artifact[Modelo campeão .pkl]
    Frontend[Interface React] --> API
    API --> Artifact
```

Componentes principais:

- **Scraping:** scripts para coleta de dados de anúncios imobiliários.
- **Pipeline de dados:** normaliza schemas, padroniza bairros e tipos de imóvel, remove duplicidades, filtra outliers e prepara as features.
- **PostgreSQL:** armazena os dados tratados com `data_salvamento`.
- **Pipeline de modelos:** executa busca de hiperparâmetros, validação cruzada, comparação de métricas e salva o modelo campeão.
- **API FastAPI:** expõe endpoints para ingestão, treinamento e predição.
- **Frontend React/Vite:** interface para predição, envio de dados e retreinamento.

## Modelos avaliados

A pipeline de modelos está organizada em `api/src/models/` e registrada em `api/src/models/registry.py`. Os modelos atualmente comparados são:

- XGBoost
- LightGBM
- CatBoost
- Random Forest
- Regressão Ridge
- Regressão Lasso
- SVR
- MLP Regressor

A seleção do modelo campeão é feita pelo menor **RMSE** médio em validação cruzada. A API também retorna **MAE** e **R²** para análise dos resultados.

## Estrutura do repositório

```text
.
|-- api/                                # Backend FastAPI e pipeline em produção
|   |-- app.py                          # Endpoints de saúde, ingestão, treino e predição
|   |-- src/
|   |   |-- pipeline_dados.py            # Limpeza, padronização e filtros dos dados
|   |   |-- pipeline_modelos.py          # Treinamento, comparação e persistência do campeão
|   |   |-- models/                      # Definições dos modelos candidatos
|   |   `-- utils/training.py            # Busca de hiperparâmetros, validação e métricas
|   |-- artifacts/                       # Modelos gerados pela API
|   |-- dataset/                         # Dados de referência usados pelo backend
|   |-- tests/                           # Testes automatizados da API e dos pipelines
|   |-- Dockerfile
|   |-- pyproject.toml
|   `-- requirements.txt
|-- front_end/                           # Interface React/Vite
|   |-- src/
|   |   |-- App.jsx                      # Tela de predição, ingestão e retreinamento
|   |   |-- main.jsx
|   |   `-- styles.css
|   |-- Dockerfile
|   |-- package.json
|   `-- vite.config.js
|-- scraping/                            # Coleta de anúncios imobiliários
|   |-- scripts/                         # Scrapers e utilitários principais
|   |-- outputs/                         # CSVs gerados por scraping
|   |-- html_scraping/                   # Páginas HTML de apoio à coleta
|   `-- imov-scraper-v1/                 # Versão alternativa/experimental do scraper
|-- tratamento de dados/                 # Notebooks e bases tratadas da etapa de limpeza
|   |-- dados_tratados/                  # Bases intermediárias de tratamento
|   `-- *.ipynb / *.csv
|-- modelagem/                           # Experimentos, notebooks e artefatos de modelos
|   |-- artifacts_modelagem/             # Rankings e modelos exportados por algoritmo
|   `-- *.ipynb
|-- specs/                               # Documentação técnica e requisitos do projeto
|   `-- capabilities/                    # Especificações por capacidade do sistema
|-- docker/
|   `-- postgres/init.sql                # Schema inicial do banco
|-- docker-compose.yml                   # Orquestração de API, frontend e PostgreSQL
|-- requirements.txt                     # Dependências Python de nível raiz
`-- README.md
```

## Como executar com Docker

Pré-requisitos:

- Docker
- Docker Compose

Na raiz do projeto, execute:

```bash
docker compose up --build
```

Serviços disponíveis:

- Frontend: `http://localhost:4173`
- API: `http://localhost:8000`
- Documentação Swagger da API: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

Credenciais padrão do banco:

```text
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=dados_imobiliarios_fortaleza
```

## Endpoints da API

### `GET /health`

Verifica se a API está online.

```bash
curl http://localhost:8000/health
```

### `POST /insertData`

Recebe um CSV bruto, executa a pipeline de tratamento e salva os dados tratados no PostgreSQL.

```bash
curl -X POST http://localhost:8000/insertData \
  -F "file=@scraping/outputs/vivareal_live_10k.csv"
```

Resposta esperada:

```json
{
  "status": "sucesso",
  "linhas_recebidas": 10000,
  "linhas_tratadas": 8500,
  "linhas_salvas": 8500,
  "resumo_filtros": []
}
```

### `POST /trainModels`

Carrega do PostgreSQL os dados salvos no último ano, treina os modelos candidatos, seleciona o campeão e salva o artefato em `api/artifacts/modelo_campeao.pkl`.

```bash
curl -X POST http://localhost:8000/trainModels
```

### `POST /predict`

Recebe as características de um imóvel e retorna o preço estimado pelo modelo campeão.

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "bairro": "Aldeota",
    "area_m2": 85,
    "quartos": 3,
    "banheiros": 2,
    "suites": 1,
    "andar": 5,
    "vagas": 2,
    "tipo_imovel_padronizado": "apartamento_padrao",
    "portaria": true,
    "vista_mar": false,
    "condominio_fechado": true,
    "piscina": true,
    "deck": false,
    "varanda_gourmet": true,
    "varanda": true,
    "academia": true,
    "salao_festa": true,
    "salao_jogos": false,
    "quadra_campo": false
  }'
```

## Interface

A interface web possui três áreas principais:

- **Predição:** formulário para preencher as características do imóvel e consultar `/predict`.
- **Inserção de dados:** upload de CSV bruto para `/insertData`.
- **Modelo:** botão de retreinamento via `/trainModels` e visualização do modelo campeão, RMSE, MAE, R² e ranking.

## Execução local sem Docker

### API

```bash
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Para usar a API localmente com PostgreSQL fora do Docker, configure:

```bash
$env:DATABASE_URL="postgresql://admin:admin@localhost:5432/dados_imobiliarios_fortaleza"
$env:CAMINHO_MODELO="artifacts/modelo_campeao.pkl"
```

### Frontend

```bash
cd front_end
npm install
npm run dev
```

Se necessário, configure a URL da API:

```bash
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
```

## Testes

Os testes ficam em `api/tests/` e cobrem partes da API, pipeline de dados e pipeline de modelos.

```bash
cd api
pytest
```

## Metodologia resumida

1. Coleta de dados reais de anúncios imobiliários via scraping.
2. Normalização dos nomes de colunas vindos de diferentes fontes.
3. Padronização de bairros, tipo de imóvel e amenidades.
4. Remoção de duplicidades por identificador e por conteúdo.
5. Filtragem de imóveis fora do escopo residencial.
6. Tratamento de outliers de preço, área, quartos, banheiros e andar.
7. Persistência dos dados tratados no PostgreSQL com data de salvamento.
8. Seleção dos registros do último ano para treinamento.
9. Treinamento com validação cruzada e busca de hiperparâmetros.
10. Comparação por RMSE, MAE e R².
11. Salvamento do modelo campeão para uso em produção pela API.

## Próximos passos

- Implementar painel de detecção de drift ou mudança significativa de preços.
- Registrar histórico de treinamentos em tabela própria.
- Adicionar autenticação para operações de ingestão e retreinamento.
- Expandir a avaliação experimental no artigo com gráficos, tabelas e análise de erro por bairro/tipo de imóvel.
- Incluir GWR com stack espacial apropriado para comparar modelos globais e locais.
