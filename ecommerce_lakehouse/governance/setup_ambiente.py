# Databricks notebook source
# Bootstrap do Unity Catalog de um ambiente: catálogo, schemas da arquitetura medalhão e Volume
# de landing, com comentários de governança. Precisa rodar antes do primeiro run do job
# principal (a extração escreve no Volume). Idempotente — pode rodar quantas vezes quiser.
#
# O catálogo usa o Default Storage da conta; por isso é criado via SQL e não por
# `databricks catalogs create`, que exige MANAGED LOCATION explícita nesse tipo de conta.
# silver e gold seriam criados pela pipeline no primeiro run de qualquer forma, mas ficam aqui
# para receberem os comentários de governança desde o início.

# COMMAND ----------
dbutils.widgets.text("catalogo", "ecommerce_lakehouse_dev")
dbutils.widgets.text("ambiente", "dev")
catalogo = dbutils.widgets.get("catalogo")
ambiente = dbutils.widgets.get("ambiente")

# COMMAND ----------
comandos = [
    f"""CREATE CATALOG IF NOT EXISTS `{catalogo}`""",
    f"""COMMENT ON CATALOG `{catalogo}` IS 'Projeto de portfólio: analytics de e-commerce em
        arquitetura medalhão (bronze/silver/gold), dashboards AI/BI e agentes Genie por diretoria
        de negócio. Ambiente: {ambiente}.'""",
    f"""CREATE SCHEMA IF NOT EXISTS `{catalogo}`.bronze""",
    f"""COMMENT ON SCHEMA `{catalogo}`.bronze IS 'Zona de pouso bruta: tabelas ingeridas via Auto
        Loader a partir do Volume de landing (dados do Supabase), sem nenhuma limpeza. Acesso
        restrito a engenharia de dados.'""",
    f"""CREATE SCHEMA IF NOT EXISTS `{catalogo}`.silver""",
    f"""COMMENT ON SCHEMA `{catalogo}`.silver IS 'Dados limpos e conformados: deduplicados,
        tipados, com regras de qualidade (@dp.expect). Acesso restrito a engenharia de dados e
        analytics engineering.'""",
    f"""CREATE SCHEMA IF NOT EXISTS `{catalogo}`.gold""",
    f"""COMMENT ON SCHEMA `{catalogo}`.gold IS 'Pronto para consumo de negócio: tabelas por
        diretoria (Comercial, Customer Success, Pricing), usadas pelos dashboards AI/BI e Genie
        Spaces. Leitura liberada para as diretorias e analistas de BI.'""",
    f"""CREATE VOLUME IF NOT EXISTS `{catalogo}`.bronze.landing""",
    f"""COMMENT ON VOLUME `{catalogo}`.bronze.landing IS 'Landing zone dos arquivos extraídos do
        bucket S3-compatível do Supabase pelo job de extração, antes da ingestão incremental via
        Auto Loader. Uma subpasta por tabela.'""",
]

for comando in comandos:
    spark.sql(" ".join(comando.split()))

display(spark.sql(f"SHOW SCHEMAS IN `{catalogo}`"))
