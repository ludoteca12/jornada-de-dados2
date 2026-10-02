# ecommerce_lakehouse

Projeto de portfólio: pipeline de analytics de e-commerce no Databricks, arquitetura
medalhão (bronze → silver → gold), dashboards AI/BI e agentes Genie por diretoria de negócio.

> A versão completa deste README (arquitetura, narrativa de negócio, prints dos dashboards)
> chega na fase de polimento do portfólio.

* `extracao/`: extração dos arquivos de origem (bucket S3-compatível do Supabase) para o Volume de landing.
* `src/ecommerce_lakehouse_etl/transformations/`: pipeline Lakeflow (bronze via Auto Loader e silver em Python, gold em SQL).
* `src/dashboards/`: dashboards AI/BI (Lakeview), um por diretoria.
* `resources/`: definição dos recursos do bundle (pipeline, job, dashboards).
* `governance/`: bootstrap do Unity Catalog e modelo de permissões por papel.
* `testes/`: notebook de testes de qualidade, roda depois do pipeline.
* `AGENTS.md`: convenções do projeto (catálogo, nomenclatura, regras de negócio).

## Setup (uma vez por workspace)

1. Rode `governance/setup.sql` num SQL warehouse (cria catálogo, schemas e Volume de landing).
2. Crie o secret scope com as credenciais S3 do Supabase:

   ```bash
   databricks secrets create-scope ecommerce_lakehouse
   databricks secrets put-secret ecommerce_lakehouse supabase_access_key_id --string-value "..."
   databricks secrets put-secret ecommerce_lakehouse supabase_secret_access_key --string-value "..."
   databricks secrets put-secret ecommerce_lakehouse supabase_endpoint_url --string-value "https://<project-ref>.supabase.co/storage/v1/s3"
   databricks secrets put-secret ecommerce_lakehouse supabase_region --string-value "..."
   databricks secrets put-secret ecommerce_lakehouse supabase_bucket --string-value "..."
   ```

3. Crie os grupos de conta em Settings > Workspace admin > Identity and access > Groups (em
   workspaces com identity federation, isso já cria grupo de conta — o único tipo aceito pelo
   Unity Catalog), com os entitlements:

   | Grupo | Entitlements |
   |---|---|
   | `engenheiro_dados` | Workspace access + Databricks SQL access |
   | `analista_bi` | Databricks SQL access |
   | `diretoria_comercial`, `diretoria_cs`, `diretoria_pricing` | Consumer access |

4. Rode `governance/grants.sql` no SQL Editor (Run all).

O acesso dos grupos aos dashboards é aplicado pelo próprio deploy (bloco `permissions` em
`resources/*.dashboard.yml`). O uso do SQL warehouse vem do grupo padrão `users`; se ele for
restringido, conceda `CAN_USE` aos grupos com `databricks warehouses update-permissions`.

## Como rodar

```bash
databricks auth login --profile <seu-perfil>
databricks bundle validate --strict --profile <seu-perfil>
databricks bundle deploy -t dev --profile <seu-perfil>
databricks bundle run ecommerce_lakehouse_job -t dev --profile <seu-perfil>
```

O job roda `extrair_dados` → `atualizar_pipeline` (bronze, silver e gold) → `testes_qualidade`.

## Governança e auditoria

Papéis e permissões estão em `governance/grants.sql`: engenharia de dados é dona do catálogo,
analistas de BI leem toda a gold e cada diretoria lê só as tabelas gold do próprio domínio.
Bronze e silver não são expostas para consumo de negócio.

Nos dashboards, cada diretoria tem `CAN_RUN` só no próprio dashboard; analistas e engenharia
têm `CAN_RUN` em todos. Os dashboards consultam com a identidade de quem está vendo
(`embed_credentials: false`), então os grants de dado valem também na tela.

**Teste de bloqueio:** um service principal membro apenas de `diretoria_cs` leu
`gold.clientes_segmentacao` (50 linhas) e recebeu `INSUFFICIENT_PRIVILEGES` em
`gold.vendas_detalhadas` e em `silver.vendas`.

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
