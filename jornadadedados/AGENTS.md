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
