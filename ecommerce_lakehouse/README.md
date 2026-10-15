# ecommerce_lakehouse — guia técnico e de reprodução

Como montar o projeto do zero num workspace seu, operar e conferir que deu certo. A visão
geral (problema de negócio, arquitetura e decisões) está no [README da raiz](../README.md).

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `extracao/` | Notebook que baixa os arquivos do bucket S3-compatível para o Volume de landing |
| `src/ecommerce_lakehouse_etl/transformations/` | Pipeline Lakeflow: bronze (Auto Loader) e silver em Python, gold em SQL |
| `src/dashboards/` | 3 dashboards AI/BI, um por diretoria |
| `src/genie/` | 3 Genie Spaces (agente por diretoria), só em prod |
| `resources/` | Recursos do bundle: pipeline, job principal, job de setup, dashboards e Genie |
| `governance/` | Bootstrap do Unity Catalog (`setup_ambiente.py`) e grants por papel (`grants.sql`) |
| `testes/` | Testes de qualidade, última task do job |
| `scripts/` | Verificação: números de referência, avaliação do Genie e teste de bloqueio |
| `seed/` | Os 4 arquivos de origem (parquet) |
| `AGENTS.md` | Convenções e regras de negócio do projeto |

## Ambientes

Um catálogo por ambiente, com os mesmos schemas e tabelas nos dois; só o catálogo muda.

| Target | Catálogo | Uso |
|---|---|---|
| `dev` (padrão) | `ecommerce_lakehouse_dev` | Desenvolvimento e testes. Recursos prefixados com `[dev <usuário>]`, agendamentos pausados. |
| `prod` | `ecommerce_lakehouse` | Único consumido pelas diretorias, dashboards publicados e Genie. Recebe os grants. |

O job principal tem agendamento diário às 6h declarado, mas pausado (`pause_status: PAUSED`
em `resources/ecommerce_lakehouse_job.job.yml`).

## Pré-requisitos

- **Databricks CLI** v1.17.0 ou mais nova (o recurso `genie_spaces` dos bundles é recente).
- **Workspace Databricks** com Unity Catalog, compute serverless, Genie e identity federation
  (grupos de conta). Testado na Free Edition.
- **SQL warehouse** chamado `Serverless Starter Warehouse` (padrão da Free Edition). Se o seu
  tiver outro nome, troque o `lookup` da variável `warehouse_id` em `databricks.yml`.
- **Bucket S3-compatível**. O projeto usa o Supabase Storage, mas qualquer endpoint S3 com
  access key funciona.
- Python 3 local, só para os scripts de verificação.

Nada no código é fixo em um workspace: o host vem do perfil da CLI, o dono de prod é quem faz
o deploy (`${workspace.current_user.userName}`) e o service principal do CI é buscado pelo
nome.

## Setup (uma vez por workspace)

### 0. Repositório e CLI

```bash
git clone https://github.com/ludoteca12/jornada-de-dados2.git
cd jornada-de-dados2/ecommerce_lakehouse          # todos os comandos abaixo rodam daqui
databricks auth login --host https://<seu-workspace>.cloud.databricks.com --profile <perfil>
```

O `<perfil>` é o nome que você escolher no login; ele é passado em todos os comandos.

### 1. Origem dos dados no Supabase

1. Crie um projeto no Supabase. Em **Storage**, crie um bucket privado (o nome é livre).
2. Suba os 4 arquivos de `seed/` **na raiz** do bucket, com os nomes originais. A extração
   procura exatamente `clientes.parquet`, `produtos.parquet`, `vendas.parquet` e
   `preco_competidores.parquet`.
3. Em **Storage → S3 Connection**, habilite o protocolo S3 e anote o **Endpoint**
   (`https://<project-ref>.supabase.co/storage/v1/s3`) e a **Region**.
4. Na mesma tela, gere uma **access key**. A secret só aparece uma vez.

Projetos gratuitos do Supabase pausam após 7 dias sem uso. Se a extração falhar por conexão,
restaure o projeto no painel.

### 2. Secret scope (compartilhado por dev e prod)

```bash
databricks secrets create-scope ecommerce_lakehouse --profile <perfil>
databricks secrets put-secret ecommerce_lakehouse supabase_access_key_id     --string-value "<access key id>"     --profile <perfil>
databricks secrets put-secret ecommerce_lakehouse supabase_secret_access_key --string-value "<secret access key>" --profile <perfil>
databricks secrets put-secret ecommerce_lakehouse supabase_endpoint_url      --string-value "https://<project-ref>.supabase.co/storage/v1/s3" --profile <perfil>
databricks secrets put-secret ecommerce_lakehouse supabase_region            --string-value "<region>"            --profile <perfil>
databricks secrets put-secret ecommerce_lakehouse supabase_bucket            --string-value "<nome do bucket>"    --profile <perfil>
```

Use `--string-value` entre aspas. No prompt interativo, alguns terminais engolem as barras do
endpoint.

### 3. Grupos de conta e service principal do CI

Em **Settings → Workspace admin → Identity and access**:

1. **Groups**: crie os grupos abaixo. Com identity federation, isso já cria grupo de conta, o
   único tipo aceito pelo Unity Catalog. `databricks groups create` cria grupo de workspace,
   que não serve.

   | Grupo | Entitlements |
   |---|---|
   | `engenheiro_dados` | Workspace access + Databricks SQL access |
   | `analista_bi` | Databricks SQL access |
   | `diretoria_comercial`, `diretoria_cs`, `diretoria_pricing` | Consumer access |

2. **Service principals**: crie `sp_ci_github`, com os entitlements Workspace access e
   Databricks SQL access. Ele **precisa existir antes do primeiro deploy**, mesmo sem usar CI,
   porque o bundle o busca pelo nome.

Os dashboards e os Genie Spaces declaram permissões para esses grupos, então o deploy falha
se eles não existirem.

## Dev

```bash
databricks bundle validate -t dev --strict --profile <perfil>
databricks bundle deploy   -t dev --profile <perfil>
databricks bundle run setup_ambiente          -t dev --profile <perfil>   # catálogo, schemas, Volume
databricks bundle run ecommerce_lakehouse_job -t dev --profile <perfil>   # extração → pipeline → testes
python scripts/verificar_numeros.py --profile <perfil> --catalogo ecommerce_lakehouse_dev
```

## Prod

Os Genie Spaces só podem ser criados depois que as tabelas gold existem: a API do Genie
rejeita tabela inexistente. Por isso o **primeiro** deploy de prod tem duas passadas.

```bash
# 1ª passada: cria pipeline, jobs e dashboards. Os 3 Genie Spaces falham com
# "Table ... does not exist" — esperado, as tabelas ainda não existem.
databricks bundle deploy -t prod --profile <perfil>

databricks bundle run setup_ambiente          -t prod --profile <perfil>
databricks bundle run ecommerce_lakehouse_job -t prod --profile <perfil>

# 2ª passada: com as tabelas criadas, os Genie Spaces sobem.
databricks bundle deploy -t prod --profile <perfil>
```

Depois:

1. Rode `governance/grants.sql` no SQL Editor (**Run all**). Grant em tabela some se a tabela
   for recriada; refresh normal mantém.
2. Publique os dashboards. O deploy cria rascunhos; o link `/published` exige publicar:
   ```bash
   databricks bundle summary -t prod -o json --profile <perfil>   # pegue os IDs em resources.dashboards
   databricks lakeview publish <dashboard_id> --profile <perfil>   # um por dashboard
   ```
3. Rode a verificação completa (próxima seção).

Nas execuções seguintes, um deploy basta.

## Como conferir que deu certo

| Script | O que prova | Resultado esperado |
|---|---|---|
| `scripts/verificar_numeros.py --catalogo <catálogo>` | Os dados atravessaram as camadas sem perda ou distorção | 19/19 números de referência |
| `scripts/avaliar_genie.py` | Os 3 agentes respondem certo as perguntas de referência | 18/18 benchmarks |
| `scripts/testar_bloqueio.py` | A governança é aplicada de fato | 1 leitura permitida, 3 negadas |

Todos recebem `--profile <perfil>` e saem com código 1 se algo divergir. O
`testar_bloqueio.py` cria um service principal temporário e o apaga no final.

Números de referência (`verificar_numeros.py`):

| Camada | Número | Valor |
|---|---|---|
| Silver | Vendas / receita total | 3.020 / R$ 974.077,28 |
| Silver | Vendas de produto não cadastrado / antes do cadastro | 20 / 5 |
| Silver | Preços de concorrente suspeitos / clientes com pronome no nome | 55 / 11 |
| Gold | Ticket médio / vendas no e-commerce | R$ 322,54 / 2.155 |
| Gold | Clientes / VIP / % da receita vinda de VIP / região de maior receita | 50 / 10 / 27,0% / Norte |
| Gold | Produtos monitorados / mais caros que todos / confirmados / suspeitos | 215 / 35 / 20 / 15 |
| Gold | Receita dos confirmados / categoria mais cara sem suspeitos | R$ 161.375,09 / Beleza |

## CI (GitHub Actions)

`.github/workflows/ci.yml` roda em todo PR e push na `main`: checa a sintaxe Python, valida os
JSON de `src/` e roda `bundle validate --strict` em dev e prod, como o service principal
`sp_ci_github`.

Para usar num fork:

1. Gere um secret OAuth para `sp_ci_github` (Service principals → `sp_ci_github` → Secrets).
   Escolha o scope **all APIs**: a CLI pede `all-apis` mesmo quando o secret é restrito.
2. No GitHub, em **Settings → Secrets and variables → Actions**:
   - secrets: `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID` (application id do SP) e
     `DATABRICKS_CLIENT_SECRET`;
   - variable: `DATABRICKS_PROD_OWNER` (email do dono de prod). Sem ela o CI ainda passa,
     mas valida a pasta do service principal em vez da pasta real de prod.
3. Faça um deploy de prod para aplicar o `CAN_MANAGE` do service principal em prod (declarado
   em `databricks.yml`).

## Agentes por diretoria (Genie)

| Agente | Tabelas | Quem usa |
|---|---|---|
| Diretoria Comercial | `vendas_temporais`, `vendas_produtos`, `vendas_detalhadas` | `diretoria_comercial` |
| Diretoria de Customer Success | `clientes_segmentacao` | `diretoria_cs` |
| Diretoria de Pricing | `precos_competitividade` | `diretoria_pricing` |

Os espaços são código (`src/genie/*.json`) e carregam as mesmas regras de negócio dos
dashboards: ticket médio sem média de médias, receita média por dia da semana e preço
suspeito que continua nas contas, mas sempre com aviso. Também trazem SQLs de exemplo e
benchmarks com a resposta esperada.

A primeira avaliação pegou três erros reais do agente, corrigidos com instruções e exemplos
explícitos:
- percentual VIP calculado sobre o próprio grupo filtrado, dando 100%;
- contagem de produtos que tirava os suspeitos;
- lista de produtos no lugar do total de receita.

Os arquivos JSON do Genie usam o nome completo do catálogo de prod (`ecommerce_lakehouse`),
porque o formato não aceita variáveis do bundle. Se mudar o nome do catálogo de prod, troque
também em `src/genie/*.json` e `governance/grants.sql`.

O Genie consulta com a identidade de quem pergunta, então os grants do Unity Catalog também
valem ali: cada espaço só inclui tabelas que a diretoria pode ler.

## Governança e auditoria

Papéis e permissões estão em `governance/grants.sql`:
- engenharia de dados é dona do catálogo;
- analistas de BI leem toda a gold;
- cada diretoria lê só as tabelas gold do próprio domínio;
- bronze e silver não são expostas para consumo de negócio.

Nos dashboards, cada diretoria tem `CAN_RUN` só no próprio dashboard; analistas e engenharia
têm `CAN_RUN` em todos. Os dashboards consultam com a identidade de quem está vendo
(`embed_credentials: false`), então os grants de dado valem também na tela.

Documentação das tabelas (os comentários de cada coluna explicam unidade e regra de cálculo):

```sql
SELECT table_schema, table_name, comment
FROM ecommerce_lakehouse.information_schema.tables
WHERE table_schema IN ('bronze', 'silver', 'gold');
```

Quem acessou o quê na gold:

```sql
SELECT event_time, user_identity.email, action_name, request_params.full_name_arg
FROM system.access.audit
WHERE service_name = 'unityCatalog'
  AND request_params.full_name_arg LIKE 'ecommerce_lakehouse.gold%'
ORDER BY event_time DESC;
```

Lineage capturado automaticamente pelo Unity Catalog (de onde cada tabela gold vem):

```sql
SELECT DISTINCT source_table_full_name, target_table_full_name
FROM system.access.table_lineage
WHERE target_table_catalog = 'ecommerce_lakehouse'
  AND source_table_full_name IS NOT NULL
ORDER BY target_table_full_name;
```
