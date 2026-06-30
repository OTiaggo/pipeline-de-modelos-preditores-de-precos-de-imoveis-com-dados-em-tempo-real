# Artigo
O artigo se encontra no arquivo `artigo final.pdf`

# Predicao de Precos de Imoveis em Fortaleza

Plataforma para ingestao, tratamento, treinamento e uso de modelos preditores de precos de imoveis em Fortaleza/CE. O projeto combina pipeline de dados, pipeline de modelos, API FastAPI, banco PostgreSQL e interface React para operar o fluxo completo: carregar dados, treinar modelos, acompanhar metricas e estimar o preco de um imovel.

## Visao geral

O sistema recebe dados brutos de imoveis em CSV, trata e padroniza as informacoes, persiste os registros em PostgreSQL e treina modelos usando apenas dados ativos do ultimo ano. A API mantem historico de ingestao, experimentos de treinamento, leaderboard dos modelos, modelo ativo e um indicador simples de drift baseado na variacao recente de precos.

Fluxo principal:

1. Upload de dados brutos pela interface ou pela rota `/insertData`.
2. Tratamento dos dados pela pipeline de dados.
3. Persistencia dos dados tratados no PostgreSQL.
4. Treinamento de modelos pela rota `/trainModels`.
5. Selecao e ativacao do melhor modelo.
6. Predicao de preco pela interface ou pela rota `/predict`.

## Contexto academico

Este repositorio tambem documenta um estudo aplicado de aprendizagem de maquina para precificacao imobiliaria. O problema foi formulado como uma tarefa de regressao supervisionada: dado um conjunto de atributos fisicos, locacionais e de infraestrutura de um imovel, o objetivo e estimar seu preco anunciado de venda.

A motivacao academica vem da natureza nao linear do mercado imobiliario. O preco nao varia apenas com area ou quantidade de quartos; ele tambem depende de bairro, tipo do imovel, vagas, infraestrutura do condominio, atributos de lazer e padrao percebido da regiao. Por isso, o projeto compara modelos lineares, SVM, redes neurais e principalmente ensembles baseados em arvores, que tendem a representar melhor interacoes e efeitos em patamares.

O trabalho completo esta descrito em `artigo.tex`, incluindo fundamentacao teorica, metodologia, experimentos, analise dos resultados e possibilidades de trabalhos futuros.

## Metodologia do estudo

A base experimental foi construida a partir de dados obtidos por web scraping de anuncios imobiliarios. A pipeline de dados padroniza o esquema de entrada, normaliza bairros e tipos de imovel, converte variaveis booleanas, calcula preco por metro quadrado e remove registros inconsistentes, duplicados, sem preco, sem metragem, nao residenciais ou fora dos cortes esperados de outliers.

No experimento principal, executado em `modelagem_busca_bayesiana.ipynb`, a base final usada na modelagem teve 3.711 imoveis validos. Foram usados atributos categoricos, numericos e booleanos para predizer `preco`. O pre-processamento combina imputacao, normalizacao de variaveis numericas e one-hot encoding para variaveis categoricas, mantendo compatibilidade com modelos sensiveis a escala e modelos baseados em arvores.

A selecao de modelos foi feita com otimizacao bayesiana de hiperparametros usando Optuna. Cada modelo foi avaliado por validacao cruzada K-Fold com tres folds, embaralhamento e semente aleatoria fixa. O objetivo de otimizacao foi minimizar o RMSE medio nos folds.

Metricas usadas:

- MAE: erro absoluto medio em reais, facil de interpretar operacionalmente.
- RMSE: erro quadratico medio em reais, penalizando mais fortemente erros grandes.
- R2: proporcao da variabilidade do preco explicada pelo modelo.

## Resultados experimentais

O experimento bayesiano comparou principalmente modelos baseados em arvores: XGBoost, LightGBM, CatBoost e Random Forest. O XGBoost obteve o melhor resultado, com desempenho muito proximo ao LightGBM, caracterizando empate tecnico na escala de precos do problema.

| Modelo | RMSE (R$) | MAE (R$) | R2 |
| --- | ---: | ---: | ---: |
| XGBoost | 414.288,80 | 232.003,72 | 0,7236 |
| LightGBM | 414.976,29 | 234.524,12 | 0,7227 |
| CatBoost | 422.171,53 | 234.471,00 | 0,7133 |
| Random Forest | 431.852,03 | 236.597,69 | 0,6999 |

Os resultados reforcam a hipotese de que modelos de arvores sao adequados para dados tabulares heterogeneos do mercado imobiliario. A analise do artigo mostra que o modelo acompanha bem a tendencia central dos precos, especialmente em imoveis ate aproximadamente R$ 3 milhoes, mas apresenta maior dispersao em imoveis de alto valor, sugerindo heterocedasticidade e possivel subestimacao de casos caros ou atipicos.

Trabalhos futuros indicados no artigo incluem transformacao logaritmica do alvo, enriquecimento geografico com distancias a pontos de interesse, modelos especializados por segmento ou faixa de preco, testes estatisticos de drift por feature e validacao temporal para simular dados futuros.

## Tecnologias

- Python 3.12
- FastAPI
- PostgreSQL 16
- Pandas e scikit-learn
- Optuna para busca bayesiana
- XGBoost, LightGBM, CatBoost, Random Forest, Ridge, Lasso, SVR e MLP
- React, Vite e lucide-react
- Docker e Docker Compose

## Estrutura do repositorio

```text
.
|-- api/                         # API FastAPI, pipelines e modelos
|   |-- app.py                   # Rotas HTTP e orquestracao do sistema
|   |-- src/pipeline_dados.py    # Tratamento e pre-processamento dos dados
|   |-- src/pipeline_modelos.py  # Treinamento e selecao de modelos
|   `-- src/models/              # Registro e configuracao dos algoritmos
|-- docker/postgres/init.sql     # Schema inicial do PostgreSQL
|-- front_end/                   # Interface React/Vite
|-- dados_tratados/              # Dados tratados e artefatos de dados
|-- scraping/                    # Coleta/scraping de dados
|-- figures/                     # Graficos usados na analise experimental
|-- specs/                       # Especificacoes do produto e arquitetura
|-- artigo.tex                   # Artigo academico do projeto
|-- modelagem_busca_bayesiana.ipynb
|-- modelagem_com_analises.ipynb
|-- docker-compose.yml           # Orquestracao local
`-- README.md
```

## Como executar com Docker

Requisitos:

- Docker
- Docker Compose

Na raiz do projeto, execute:

```bash
docker compose up --build
```

Servicos disponiveis apos a subida:

- Interface: `http://localhost:4173`
- API: `http://localhost:8000`
- Documentacao Swagger: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

Credenciais padrao do banco local:

```text
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=dados_imobiliarios_fortaleza
```

## Como executar localmente sem Docker

### API

```bash
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Por padrao, a API espera um PostgreSQL em:

```text
postgresql://admin:admin@localhost:5432/dados_imobiliarios_fortaleza
```

Tambem e possivel configurar via variaveis de ambiente:

```text
DATABASE_URL=postgresql://admin:admin@localhost:5432/dados_imobiliarios_fortaleza
CAMINHO_MODELO=artifacts/modelo_campeao.pkl
ARTIFACTS_MODELOS_DIR=artifacts/modelos
```

### Front-end

```bash
cd front_end
npm install
npm run dev
```

O front-end usa `http://127.0.0.1:8000` como API padrao. Para mudar:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Funcionalidades

### Predicao de preco

A interface possui uma pagina para informar atributos do imovel e consultar o preco estimado pelo modelo ativo. A API retorna o valor estimado e uma explicacao simples baseada nas features mais importantes do modelo ativo.

### Ingestao de dados

Permite upload de arquivos CSV com dados brutos. A pipeline trata os registros, salva os dados tratados no PostgreSQL e registra metadados do lote, como arquivo, quantidade de linhas recebidas, linhas tratadas, linhas salvas e status.

### Treinamento de modelos

Permite iniciar experimentos de treinamento com modelos selecionados, busca bayesiana ou grid manual e numero configuravel de tentativas. O treinamento usa dados ativos do ultimo ano, salva artefatos versionados, registra metricas e ativa o modelo campeao.

### Operacao de modelos

A plataforma exibe modelo ativo, historico de experimentos, leaderboard, logs de treinamento, importancia de features e indicador de drift. Tambem permite ativar modelos anteriores ja treinados.

## Features usadas no modelo

Alvo:

- `preco`

Features categoricas:

- `bairro`
- `tipo_imovel_padronizado`

Features numericas:

- `area_m2`
- `quartos`
- `banheiros`
- `suites`
- `andar`
- `vagas`

Features booleanas:

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

## Principais rotas da API

| Metodo | Rota | Descricao |
| --- | --- | --- |
| `GET` | `/health` | Verifica se a API esta online. |
| `POST` | `/insertData` | Recebe um CSV bruto, trata e salva os dados no PostgreSQL. |
| `GET` | `/data/status` | Retorna resumo dos dados ativos. |
| `GET` | `/data/ingestions` | Lista lotes de ingestao. |
| `POST` | `/data/ingestions/{id_lote}/rollback` | Desativa registros de um lote de ingestao. |
| `POST` | `/trainModels` | Inicia treinamento assincrono de modelos. |
| `GET` | `/training/{id_experimento}` | Consulta status e resultados de um experimento. |
| `GET` | `/training/{id_experimento}/logs` | Consulta logs de treinamento. |
| `GET` | `/models/history` | Lista historico de experimentos. |
| `GET` | `/models/leaderboard` | Lista modelos treinados ordenados por desempenho. |
| `GET` | `/models/active` | Retorna o modelo atualmente ativo. |
| `POST` | `/models/{id_modelo}/activate` | Ativa um modelo treinado. |
| `GET` | `/models/{id_modelo}/feature-importance` | Retorna importancia de features do modelo. |
| `GET` | `/model-health/drift` | Retorna indicador de drift/preco recente. |
| `POST` | `/predict` | Prediz o preco de um imovel com o modelo ativo. |

## Exemplo de predicao

```bash
curl -X POST http://localhost:8000/predict ^
  -H "Content-Type: application/json" ^
  -d "{
    \"bairro\": \"Aldeota\",
    \"area_m2\": 85,
    \"quartos\": 3,
    \"banheiros\": 2,
    \"suites\": 1,
    \"andar\": 5,
    \"vagas\": 2,
    \"tipo_imovel_padronizado\": \"apartamento_padrao\",
    \"portaria\": true,
    \"vista_mar\": false,
    \"condominio_fechado\": true,
    \"piscina\": true,
    \"deck\": false,
    \"varanda_gourmet\": false,
    \"varanda\": true,
    \"academia\": true,
    \"salao_festa\": true,
    \"salao_jogos\": false,
    \"quadra_campo\": false
  }"
```

Antes de usar `/predict`, e necessario existir um modelo ativo. Caso ainda nao exista, envie dados e execute `/trainModels`.

## Modelos disponiveis

O registro atual de modelos inclui:

- XGBoost
- LightGBM
- CatBoost
- Random Forest
- Ridge
- Lasso
- SVR
- MLP

GWR aparece como possibilidade futura, mas depende de uma stack espacial especifica e ainda nao esta ativo no registro de treinamento.

## Documentacao do projeto

As especificacoes funcionais e arquiteturais ficam em `specs/`, incluindo:

- `specs/product.md`
- `specs/architecture.md`
- `specs/domain.md`
- `specs/quality.md`
- `specs/capabilities/`

Artefatos academicos e experimentais:

- `artigo.tex`: texto academico do projeto.
- `artigo final.pdf`: versao renderizada do artigo.
- `modelagem_busca_bayesiana.ipynb`: experimento principal com Optuna.
- `modelagem_com_analises.ipynb`: analises exploratorias e diagnosticos.
- `figures/`: graficos comparativos, valores reais versus previstos e residuos.

## Apresentacao

Link da apresentacao:

https://gamma.app/docs/Predicao-de-Precos-de-Imoveis-em-Fortaleza-uztc2kmhj4e9twl
