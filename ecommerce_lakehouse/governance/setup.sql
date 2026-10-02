-- Bootstrap do Unity Catalog: objetos que precisam existir ANTES do primeiro
-- `databricks bundle deploy`. Idempotente (IF NOT EXISTS), pode ser rodado mais de uma vez.
--
-- O catálogo usa o Default Storage da conta; por isso é criado via SQL e não por
-- `databricks catalogs create`, que exige MANAGED LOCATION explícita nesse tipo de conta.
-- silver e gold seriam criados pela pipeline no primeiro run de qualquer forma, mas ficam
-- aqui para receberem os comentários de governança desde o início.
--
-- Além deste script, a extração precisa do secret scope "ecommerce_lakehouse" com as chaves
-- supabase_access_key_id, supabase_secret_access_key, supabase_endpoint_url, supabase_region
-- e supabase_bucket (veja o README).

CREATE CATALOG IF NOT EXISTS ecommerce_lakehouse
COMMENT 'Projeto de portfólio: analytics de e-commerce em arquitetura medalhão (bronze/silver/gold), dashboards AI/BI e agentes Genie por diretoria de negócio.';

CREATE SCHEMA IF NOT EXISTS ecommerce_lakehouse.bronze
COMMENT 'Zona de pouso bruta: tabelas ingeridas via Auto Loader a partir do Volume de landing (dados do Supabase), sem nenhuma limpeza. Acesso restrito a engenharia de dados.';

CREATE SCHEMA IF NOT EXISTS ecommerce_lakehouse.silver
COMMENT 'Dados limpos e conformados: deduplicados, tipados, com regras de qualidade (@dp.expect). Acesso restrito a engenharia de dados e analytics engineering.';

CREATE SCHEMA IF NOT EXISTS ecommerce_lakehouse.gold
COMMENT 'Pronto para consumo de negócio: tabelas por diretoria (Comercial, Customer Success, Pricing), usadas pelos dashboards AI/BI e Genie Spaces. Leitura liberada para as diretorias e analistas de BI.';

CREATE VOLUME IF NOT EXISTS ecommerce_lakehouse.bronze.landing
COMMENT 'Landing zone dos arquivos extraídos do bucket S3-compatível do Supabase pelo job de extração, antes da ingestão incremental via Auto Loader. Uma subpasta por tabela.';
