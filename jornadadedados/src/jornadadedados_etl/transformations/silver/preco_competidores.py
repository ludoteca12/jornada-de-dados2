# A coleta de preços de concorrentes roda em paralelo por produto e pode duplicar a
# combinação produto+concorrente numa mesma leva. data_coleta chega como texto porque a
# origem varia o formato entre execuções. Comparamos com o preco_atual já limpo da
# silver.produtos (não o bruto da bronze) para não propagar erro de tipo/duplicata para
# o cálculo de preco_suspeito.
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType


@dp.materialized_view(
    name="preco_competidores",
    comment="Preços de concorrentes deduplicados por produto+concorrente, com marcação de preço suspeito.",
)
@dp.expect_all_or_fail(
    {
        "id_produto_preenchido": "id_produto IS NOT NULL",
        "preco_concorrente_positivo": "preco_concorrente > 0",
    }
)
@dp.expect("preco_plausivel", "NOT preco_suspeito")
def preco_competidores():
    bronze = spark.read.table("bronze.preco_competidores").dropDuplicates(
        ["id_produto", "nome_concorrente"]
    )
    produtos = spark.read.table("silver.produtos").select(
        "id_produto", F.col("preco_atual").alias("_preco_atual")
    )

    df = bronze.join(produtos, "id_produto", "left")

    preco_concorrente = F.col("preco_concorrente").cast(DecimalType(10, 2))

    return df.select(
        "id_produto",
        "nome_concorrente",
        preco_concorrente.alias("preco_concorrente"),
        F.to_timestamp(F.col("data_coleta")).alias("data_coleta"),
        (preco_concorrente < (F.col("_preco_atual") * 0.6)).alias("preco_suspeito"),
    )
