-- Modelo de permissões por papel para o catálogo de PROD (ecommerce_lakehouse). O catálogo de
-- dev (ecommerce_lakehouse_dev) não recebe grants: só quem desenvolve acessa.
--
-- Grant em tabela some se a tabela for recriada (destroy da pipeline, full refresh que troque
-- o dono). Refresh normal das materialized views mantém os grants. Rode de novo nesses casos.
--
-- Pré-requisito: os grupos abaixo precisam existir como grupos de CONTA (account-level). Grupo
-- de workspace (legado) não é aceito em GRANT do Unity Catalog. Em workspaces com identity
-- federation, criar o grupo em Settings > Workspace admin > Identity and access > Groups já
-- cria um grupo de conta, veja a seção Setup do README.
--
-- Para ler uma tabela são necessárias três permissões encadeadas: USE CATALOG no catálogo,
-- USE SCHEMA no schema e SELECT na tabela (ou no schema inteiro). Permissão concedida num
-- nível herda para baixo, inclusive para tabelas criadas depois.
--
-- Papéis:
--   engenheiro_dados     -> dono da bronze/silver/gold, acesso total ao catálogo.
--   analista_bi          -> leitura em toda a gold (constrói dashboards e análises ad-hoc).
--   diretoria_comercial  -> leitura só nas tabelas gold de vendas.
--   diretoria_cs         -> leitura só em gold.clientes_segmentacao.
--   diretoria_pricing    -> leitura só em gold.precos_competitividade.
--
-- Bronze e silver nunca são expostas para consumo de negócio.

-- engenheiro_dados: acesso total ao catálogo.
GRANT USE CATALOG, USE SCHEMA ON CATALOG ecommerce_lakehouse TO engenheiro_dados;
GRANT ALL PRIVILEGES ON SCHEMA ecommerce_lakehouse.bronze TO engenheiro_dados;
GRANT ALL PRIVILEGES ON SCHEMA ecommerce_lakehouse.silver TO engenheiro_dados;
GRANT ALL PRIVILEGES ON SCHEMA ecommerce_lakehouse.gold TO engenheiro_dados;

-- analista_bi: leitura em toda a gold.
GRANT USE CATALOG ON CATALOG ecommerce_lakehouse TO analista_bi;
GRANT USE SCHEMA, SELECT ON SCHEMA ecommerce_lakehouse.gold TO analista_bi;

-- Cada diretoria lê só as tabelas gold do próprio domínio.
GRANT USE CATALOG ON CATALOG ecommerce_lakehouse TO diretoria_comercial;
GRANT USE SCHEMA ON SCHEMA ecommerce_lakehouse.gold TO diretoria_comercial;
GRANT SELECT ON TABLE ecommerce_lakehouse.gold.vendas_temporais TO diretoria_comercial;
GRANT SELECT ON TABLE ecommerce_lakehouse.gold.vendas_produtos TO diretoria_comercial;
GRANT SELECT ON TABLE ecommerce_lakehouse.gold.vendas_detalhadas TO diretoria_comercial;

GRANT USE CATALOG ON CATALOG ecommerce_lakehouse TO diretoria_cs;
GRANT USE SCHEMA ON SCHEMA ecommerce_lakehouse.gold TO diretoria_cs;
GRANT SELECT ON TABLE ecommerce_lakehouse.gold.clientes_segmentacao TO diretoria_cs;

GRANT USE CATALOG ON CATALOG ecommerce_lakehouse TO diretoria_pricing;
GRANT USE SCHEMA ON SCHEMA ecommerce_lakehouse.gold TO diretoria_pricing;
GRANT SELECT ON TABLE ecommerce_lakehouse.gold.precos_competitividade TO diretoria_pricing;
