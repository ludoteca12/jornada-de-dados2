# Ingestão incremental via Auto Loader: cada arquivo novo pousado em
# /Volumes/ecommerce_lakehouse/bronze/landing/vendas pelo job de extração (extracao/
# extrair_dados.py) é lido uma única vez e acumulado aqui, sem nenhuma limpeza — isso é
# trabalho da silver. _arquivo_origem e _data_ingestao existem para rastreabilidade.
from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.table(
    name="bronze.vendas",
    comment="Vendas brutas, ingeridas via Auto Loader a partir do Volume de landing. Sem limpeza.",
)
def vendas():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "parquet")
        .option(
            "cloudFiles.schemaLocation",
            "/Volumes/ecommerce_lakehouse/bronze/landing/_schemas/vendas",
        )
        .load("/Volumes/ecommerce_lakehouse/bronze/landing/vendas/")
        .select(
            "*",
            F.col("_metadata.file_path").alias("_arquivo_origem"),
            F.current_timestamp().alias("_data_ingestao"),
        )
    )
