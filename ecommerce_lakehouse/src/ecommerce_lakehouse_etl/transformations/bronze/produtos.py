# Ingestão incremental via Auto Loader: cada arquivo novo pousado em
# /Volumes/<catálogo>/bronze/landing/produtos pelo job de extração (extracao/extrair_dados.py) é
# lido uma única vez e acumulado aqui, sem nenhuma limpeza — isso é trabalho da silver.
# _arquivo_origem e _data_ingestao existem para rastreabilidade: se um número bater errado lá
# na frente, dá pra saber de qual arquivo e quando aquele dado chegou. O catálogo vem da
# configuração da pipeline, então o mesmo código lê o Volume de dev ou de prod.
from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.table(
    name="bronze.produtos",
    comment="Produtos brutos, ingeridos via Auto Loader a partir do Volume de landing. Sem limpeza.",
)
def produtos():
    landing = f"/Volumes/{spark.conf.get('catalogo')}/bronze/landing"
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "parquet")
        .option("cloudFiles.schemaLocation", f"{landing}/_schemas/produtos")
        .load(f"{landing}/produtos/")
        .select(
            "*",
            F.col("_metadata.file_path").alias("_arquivo_origem"),
            F.current_timestamp().alias("_data_ingestao"),
        )
    )
