# ecommerce_lakehouse

Portfolio e-commerce analytics project on Databricks: medallion architecture (bronze → silver
→ gold), AI/BI dashboards and Genie agents per business directorate, built as a Declarative
Automation Bundle (DAB).

## For AI Agents: Use Databricks AI Tools

**BEFORE any other action, read the `databricks-core` skill.**

It sets you up to work with this project reliably: CLI authentication, profile
selection, data discovery, and the bundle deployment workflow. Without it,
results are often slower and less accurate.

If this skill is not available (Databricks AI Tools are not installed), you can install them for your coding agent in seconds:

```bash
databricks aitools install
```

If the CLI is not installed, see: https://docs.databricks.com/dev-tools/cli/install

---

## Project Instructions

- Um catálogo por ambiente, mesmos schemas (`bronze`, `silver`, `gold`) e tabelas nos dois:
  `ecommerce_lakehouse_dev` (target `dev`, default) e `ecommerce_lakehouse` (target `prod`,
  o único consumido por diretorias, dashboards publicados e Genie). Nunca fixar o nome do
  catálogo em código: ele vem de `${var.catalog}`, parâmetro `catalogo` nos notebooks e
  `spark.conf.get("catalogo")` na pipeline.
- Desenvolver e testar sempre em dev (`-t dev`); prod só recebe deploy de código já
  validado em dev.
- Pipeline não troca de catálogo: o deploy aceita a mudança, mas o run falha em loop com
  `Can not move tables across catalogs`. Para mudar o catálogo de um target, apagar a
  pipeline e redeployar; as tabelas antigas não saem em cascata (a cascata só vale para o
  catálogo atual) e precisam de DROP explícito.
- Nomes de tabelas e colunas em português, snake_case, sem acento.
- Bronze e silver em Python (`from pyspark import pipelines as dp`), gold em SQL.
- Um arquivo por tabela: `transformations/<camada>/<tabela>.py|.sql`.
- Extração (`extracao/extrair_dados.py`, task do job) baixa os arquivos do Supabase para o
  Volume `bronze.landing`, uma subpasta por tabela. Credenciais só via secret scope
  `ecommerce_lakehouse`, nunca em código.
- Bronze = streaming tables com Auto Loader lendo do Volume (ingestão incremental, sem
  limpeza, com `_arquivo_origem`/`_data_ingestao`). Silver e gold = materialized views com
  leitura batch (`spark.read.table`), recalculadas por inteiro a cada run.
- Pipeline serverless, catálogo do ambiente, schema padrão `silver`. Tabelas fora
  do schema padrão SEMPRE com o schema no nome (`name="bronze.clientes"`, `gold.<tabela>`)
  — sem isso a tabela cai em `silver` e colide com a silver de mesmo nome. Nomes no código
  sempre `schema.tabela`, sem catálogo.
- Cada arquivo de transformação começa com um comentário explicando o PORQUÊ das regras
  (em português), não o que o código faz.
- Dinheiro sempre `DECIMAL(10,2)`.
- Problema de qualidade conhecido é marcado em uma coluna e medido com `@dp.expect`
  (warn). Nunca descartar linhas, ex.: apagar vendas mudaria a receita.
- `@dp.expect_all_or_fail` só para o que nunca pode acontecer (chaves/campos
  obrigatórios, valores que sempre devem ser positivos, etc.).
- Sempre rodar `databricks bundle validate --strict` antes do deploy.
- CLI: use `--profile dbc-b2999451-9f53` (perfil válido para
  `https://dbc-b2999451-9f53.cloud.databricks.com`).

## Governança (Unity Catalog)

- Objetos que precisam existir antes do primeiro run (catálogo, schemas, Volume de landing,
  comentários) ficam em `governance/setup_ambiente.py`, rodado pelo job `setup_ambiente`
  (`databricks bundle run setup_ambiente -t <dev|prod>`) — idempotente. Schema ou Volume novo
  entra lá, nunca criado só pela UI/CLI sem registro no repo.
- `governance/grants.sql` é só de prod; o catálogo de dev não recebe grants. Grant em tabela
  some se a tabela for recriada, rodar de novo nesse caso.
- Modelo de permissões por papel em `governance/grants.sql` (engenheiro_dados, analista_bi e
  um grupo por diretoria, cada um lendo só a gold do próprio domínio). GRANT do Unity Catalog
  só aceita grupos de conta (account-level): criar pela UI do workspace (Identity and access >
  Groups) ou pela API `/api/2.0/account/scim/v2/Groups`. `databricks groups create` cria
  grupo de workspace (legado) e não serve.
- Entitlements dos grupos (workspace): engenheiro_dados = Workspace access + Databricks SQL
  access; analista_bi = Databricks SQL access; diretorias = Consumer access. Nenhum com Admin.
- Grants nunca para usuário individual, sempre para grupo.
- Acesso aos dashboards declarado no bloco `permissions` de cada `resources/*.dashboard.yml`:
  diretoria dona do domínio, analista_bi e engenheiro_dados com `CAN_RUN`. Ninguém recebe
  `CAN_EDIT` — dashboard é código, edição feita pela UI é sobrescrita no próximo deploy.
- Bronze e silver não são liberadas para consumo de negócio, diretorias e BI leem só gold.

## Convenções da camada gold (valem para todas as diretorias)

- SQL, um arquivo por tabela em `transformations/gold/`,
  `CREATE OR REFRESH MATERIALIZED VIEW gold.<tabela>`.
- Declarar TODAS as colunas entre parênteses com tipo e `COMMENT` (sem o tipo, o
  comentário é ignorado), e `COMMENT` na tabela dizendo quando usar. Comentários em
  português, com unidade (R$), regra de cálculo e avisos que evitem erro do Genie (a IA
  que gera SQL a partir de perguntas em português) e do dashboard.
- Incluir TODAS as vendas nas golds de receita, inclusive de produto não cadastrado:
  dinheiro que entrou é receita.
- Período dos dados do e-commerce: 13/12/2025 a 11/01/2026.
- Toda gold nova ganha testes no notebook `testes/testes_qualidade.py`.

## Convenções de dashboards AI/BI (valem para todas as diretorias)

- Um arquivo por dashboard: `src/dashboards/<nome>.lvdash.json`, com o recurso em
  `resources/<nome>.dashboard.yml`.
- `warehouse_id` do recurso vem de `${var.warehouse_id}`, uma variável do bundle com
  `lookup` pelo nome do warehouse ("Serverless Starter Warehouse") declarada em
  `databricks.yml`. `dataset_catalog` do recurso = `${var.catalog}`; `dataset_schema` =
  `gold`.
- Toda query dentro do `.lvdash.json` usa nome de tabela puro (`FROM vendas_detalhadas`),
  sem catálogo nem schema, o mesmo dashboard funciona em dev e prod.
- Tudo em português: título, subtítulo (com período e fonte dos dados), nomes de gráficos e
  eixos. Canal exibido como "E-commerce"/"Loja física" (o dado cru é
  `ecommerce`/`loja_fisica`, mapear com CASE na query). Dinheiro em R$.
- Layout de leitura rápida: título, uma linha de KPIs, gráficos, tabela de detalhe para agir.
- Regras que nenhum gráfico pode quebrar: ticket médio é receita total ÷ número de vendas,
  nunca média de médias; nunca somar `clientes_unicos` entre linhas de `vendas_temporais`;
  produto se conta por `id_produto` (nomes se repetem); dia da semana se compara pela
  receita MÉDIA por dia (o período tem 5 sábados e 5 domingos e só 4 de cada dia útil, não
  dá pra comparar por soma direto). Data e hora estão em UTC: dizer isso no eixo.
  `diferenca_pct_vs_media`/`diferenca_pct_vs_minimo` (em `gold.precos_competitividade`) estão
  em pontos percentuais (10 = 10%): não usar formato de porcentagem 0-1 sem dividir por 100
  antes.

## Convenções dos Genie Spaces (agente por diretoria)

- Um espaço por diretoria: `src/genie/<nome>.json` (serialized space), declarado em
  `resources/genie_spaces.yml` só no target `prod`. É a única exceção à regra de não fixar
  catálogo: o arquivo do Genie não aceita variáveis do bundle, então as tabelas usam o nome
  completo `ecommerce_lakehouse.gold.<tabela>`.
- Cada espaço só inclui tabelas que a diretoria tem GRANT para ler, o Genie consulta com a
  identidade de quem pergunta. Permissões: diretoria dona, analista_bi e engenheiro_dados com
  `CAN_RUN`.
- Conteúdo: instruções de negócio (mesmas regras dos dashboards), perguntas de exemplo, SQLs
  de exemplo confiáveis e benchmarks com a resposta esperada. Todo SQL de exemplo/benchmark é
  executado no warehouse antes do deploy.
- O Genie não é determinístico: mesma pergunta pode sair certa ou errada. Validar com
  `databricks genie genie-create-eval-run <space_id>` (meta: todos os benchmarks GOOD) e
  repetir ao vivo (`databricks genie start-conversation`) as perguntas sensíveis. Erro de
  cálculo se corrige com instrução + SQL de exemplo explícitos, não só com benchmark (o
  benchmark só mede, não ensina).
- Toda mudança de instrução: rodar a avaliação de novo nos três espaços.

## Números de referência (conferidos por SQL direto após cada prompt)

Período dos dados: 13/12/2025 a 11/01/2026. Esses números servem de regressão, se uma
mudança futura na bronze/silver/gold fizer algum deles sair do lugar, investigar antes de
seguir.

- **Prompt 1 (silver)**: 3.020 vendas, receita total R$ 974.077,28; 20 vendas de produto não
  cadastrado (R$ 4.240,01); 5 vendas antes do cadastro do produto (R$ 325,88); 55 preços de
  concorrente suspeitos; 11 clientes com pronome de tratamento no cadastro. Clientes por
  região: Norte 17, Nordeste 12, Centro-Oeste 9, Sudeste 8, Sul 4.
- **Prompt 2 (`gold.clientes_segmentacao`)**: 50 clientes, 10 VIP, 25 TOP_TIER, 15 REGULAR;
  receita R$ 974.077,28 (igual à silver); maior cliente Ana Sophia Pereira (MG, R$ 30.716,63).
- **Prompt 3 (`gold.vendas_temporais`/`vendas_produtos`/`vendas_detalhadas`)**: receita e
  3.020 vendas batendo com a silver nas 3 tabelas; 2.155 vendas no canal `ecommerce` (R$
  705.486,21), ticket médio geral R$ 322,54.
- **Prompt 4 (`gold.precos_competitividade`)**: 215 produtos monitorados; 35
  `MAIS_CARO_QUE_TODOS`, dos quais 20 confirmados (sem preço suspeito, R$ 161.375,09 de
  receita) e 15 com preço suspeito (categoria Tênis, sem nenhuma venda, +100% acima da média
  do mercado, produto com preço suspeito continua em todas as contas, só precisa ser
  conferido); 6 `MAIS_BARATO_QUE_TODOS`; excluindo os suspeitos, Beleza é a categoria mais
  cara (+1,24% vs. média dos concorrentes).
- **Prompt 5 (dashboards AI/BI)**: 3 dashboards publicados (Diretoria Comercial, Diretoria de
  Customer Success, Diretoria de Pricing), todos conferidos contra os mesmos números acima.
- **Genie Spaces**: 18/18 benchmarks GOOD (6 por espaço). Perguntas sensíveis estáveis em
  3 repetições ao vivo: % da receita VIP = 27,0%; 35 produtos mais caros que todos (com aviso
  dos 15 suspeitos); receita dos confirmados = R$ 161.375,09.
