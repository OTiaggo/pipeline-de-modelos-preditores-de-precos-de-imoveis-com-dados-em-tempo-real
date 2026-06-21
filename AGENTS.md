# Contextualização do projeto
O projeto consiste em um treinamento automatizados de modelos com a finalidade de predição de valores de imóveis na cidade de Fortaleza/Ce. Usamos dados atualizados extraídos via web scraping.

O projeto conta com uma pipeline de dados, de modelos, uma api e uma interface para interagir com o sistema, uma plataforma de predição completa.

Os modelos são retreinados conforme o desejo do usuário, e além disso, o sistema consegue identificar sozinha a mudança significativa de preços sinalizando a necessidade de retreino com os dados atualizados. 

Por meio da interface o usuario pode inserir atributos sobre um imovel e predizer, a partir do melhjo modelo treinado, qual o valor estimado para aquele imovel.



# Features
## Escolha das features
- bairro
- area_m2
- quartos
- banheiros
- suites
- andar
- vagas
- portaria
- vista_mar
- condominio_fechado
- piscina
- deck
- varanda_gourmet
- varanda
- academia
- salao_festa
- salao_jogos
- quadra_campo
- tipo_imovel_padronizado

## Alvo
- preco

# Engenharia do sistema

## Pipelines
O sistema contará com a pipeline automatizada de dados e de modelos.

### Pipeline de dados
Receberá os dados brutos e fará o tratamento para posteriormente ser feito o novo treinamento do modelo. Os dados tratados ficarão salvos em um banco de dados Postgres.

### Pipeline de modelos
Usará os dados tratados pela pipeline de dados. Usará para treinamento apenas os dados no período do último ano para que dados de preços passados nao alterem o desempenho do modelo.

A pipeline vai executar um grid-search com os seguintes modelos:
- regressão linear
- redes neurais 
- svm

- Regressão Linear Múltipla (com Regularização Ridge ou Lasso)
- GWR (Geographically Weighted Regression)

- catBoost
- LightGBM
- XGBoost
- Random Forest

Usaremos a estratégia de bayesian grid search tambem

## Api 
A API vai ter as seguintes requisições:

### /insertData
Vai receber os dados brutos em formato csv. Os dados serão carregado e tratado pela pipeline de dados.

Ao receber novos dados, ele trata e salva no banco de dados Postgres. Salva também a data em que foi salvo, para que conseguirmos puxar apenas dados de um ano.

### /trainModels
Vai acionar a pipeline de modelos para fazer o grid search com os modelos selecionados e selecionar o melhor para ser usado pelo sistema.

Vai puxar os dados do ultimo ano do banco de dados.

### /predict
Recebe atributos de um imóvel para fazer a predição do seu preço.
