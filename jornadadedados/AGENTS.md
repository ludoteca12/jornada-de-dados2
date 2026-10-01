# Declarative Automation Bundles Project

This project uses Declarative Automation Bundles (DABs) for deployment. Add project-specific instructions below.

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

- Catálogo `jornada-de-dados` (schemas `bronze`, `silver`, `gold`). Nunca use outro catálogo.
  Nomes de catálogo/schema hifenizados precisam de crase em SQL: `` `jornada-de-dados`.bronze.vendas ``.
- Nomes de tabelas e colunas em português, snake_case, sem acento.
- Silver em Python (`from pyspark import pipelines as dp`), gold em SQL.
- Um arquivo por tabela: `transformations/silver/<tabela>.py` e `transformations/gold/<tabela>.sql`.
- Todas as tabelas são materialized views com leitura batch (`spark.read.table`), nunca
  streaming table — a bronze é sobrescrita a cada execução.
- Pipeline serverless, catálogo `jornada-de-dados`, schema padrão `silver`. Golds
  publicadas como `gold.<tabela>`. Nomes no código sempre `schema.tabela`, sem catálogo.
- Cada arquivo de transformação começa com um comentário explicando o PORQUÊ das regras
  (em português), não o que o código faz.
- Dinheiro sempre `DECIMAL(10,2)`.
- Problema de qualidade conhecido é marcado em uma coluna e medido com `@dp.expect`
  (warn). Nunca descartar linhas — ex.: apagar vendas mudaria a receita.
- `@dp.expect_all_or_fail` só para o que nunca pode acontecer (chaves/campos
  obrigatórios, valores que sempre devem ser positivos, etc.).
- Sempre rodar `databricks bundle validate --strict` antes do deploy.
- CLI: use `--profile dbc-b2999451-9f53` (perfil válido para
  `https://dbc-b2999451-9f53.cloud.databricks.com`).

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
  sem catálogo nem schema — o mesmo dashboard funciona em dev e prod.
- Tudo em português: título, subtítulo (com período e fonte dos dados), nomes de gráficos e
  eixos. Canal exibido como "E-commerce"/"Loja física" (o dado cru é
  `ecommerce`/`loja_fisica`, mapear com CASE na query). Dinheiro em R$.
- Layout de leitura rápida: título, uma linha de KPIs, gráficos, tabela de detalhe para agir.
- Regras que nenhum gráfico pode quebrar: ticket médio é receita total ÷ número de vendas,
  nunca média de médias; nunca somar `clientes_unicos` entre linhas de `vendas_temporais`;
  produto se conta por `id_produto` (nomes se repetem); dia da semana se compara pela
  receita MÉDIA por dia (o período tem 5 sábados e 5 domingos e só 4 de cada dia útil — não
  dá pra comparar por soma direto). Data e hora estão em UTC: dizer isso no eixo.
  `diferenca_pct_vs_media`/`diferenca_pct_vs_minimo` (em `gold.precos_competitividade`) estão
  em pontos percentuais (10 = 10%): não usar formato de porcentagem 0-1 sem dividir por 100
  antes.

## Números de referência (conferidos por SQL direto após cada prompt)

Período dos dados: 13/12/2025 a 11/01/2026. Esses números servem de regressão — se uma
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
  do mercado — produto com preço suspeito continua em todas as contas, só precisa ser
  conferido); 6 `MAIS_BARATO_QUE_TODOS`; excluindo os suspeitos, Beleza é a categoria mais
  cara (+1,24% vs. média dos concorrentes).
- **Prompt 5 (dashboards AI/BI)**: 3 dashboards publicados (Diretoria Comercial, Diretoria de
  Customer Success, Diretoria de Pricing), todos conferidos contra os mesmos números acima.
