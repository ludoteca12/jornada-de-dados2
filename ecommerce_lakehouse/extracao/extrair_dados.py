# Databricks notebook source
# Extração: baixa os arquivos de origem do bucket S3-compatível do Supabase e pousa no Volume
# de landing da bronze. Não existe External Location/Storage Credential do Unity Catalog para
# um endpoint S3-compatível arbitrário (isso só é suportado para AWS S3, Azure ADLS, GCS e
# Cloudflare R2) — por isso a extração é feita em Python puro via boto3 (chamadas HTTPS
# diretas à API S3, sem depender de um conector de filesystem do Spark), pousando os arquivos
# num Volume do Unity Catalog. A partir daí, a ingestão incremental de verdade (Auto Loader)
# acontece nas tabelas bronze do pipeline Lakeflow. As credenciais nunca ficam em código:
# vêm todas do secret scope "ecommerce_lakehouse", compartilhado por dev e prod (a origem é a
# mesma). O catálogo de destino chega como parâmetro do job, um por ambiente.

# COMMAND ----------
# MAGIC %pip install --quiet boto3

# COMMAND ----------
dbutils.library.restartPython()

# COMMAND ----------
import os

import boto3
from botocore.client import Config

dbutils.widgets.text("catalogo", "ecommerce_lakehouse_dev")
catalogo = dbutils.widgets.get("catalogo")

SCOPE = "ecommerce_lakehouse"
VOLUME_BASE = f"/Volumes/{catalogo}/bronze/landing"
ARQUIVOS = ["clientes.parquet", "produtos.parquet", "vendas.parquet", "preco_competidores.parquet"]

access_key = dbutils.secrets.get(SCOPE, "supabase_access_key_id")
secret_key = dbutils.secrets.get(SCOPE, "supabase_secret_access_key")
endpoint_url = dbutils.secrets.get(SCOPE, "supabase_endpoint_url")
region = dbutils.secrets.get(SCOPE, "supabase_region")
bucket = dbutils.secrets.get(SCOPE, "supabase_bucket")

# COMMAND ----------
s3 = boto3.client(
    "s3",
    endpoint_url=endpoint_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name=region,
    config=Config(s3={"addressing_style": "path"}),
)

# COMMAND ----------
for arquivo in ARQUIVOS:
    tabela = arquivo.removesuffix(".parquet")
    destino_dir = f"{VOLUME_BASE}/{tabela}"
    destino_arquivo = f"{destino_dir}/{arquivo}"

    os.makedirs(destino_dir, exist_ok=True)
    s3.download_file(bucket, arquivo, destino_arquivo)
    tamanho = os.path.getsize(destino_arquivo)
    print(f"{arquivo} -> {destino_arquivo} ({tamanho} bytes)")
