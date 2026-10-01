# A bronze é sobrescrita a cada ingestão e pode trazer o mesmo id_produto mais de uma vez
# (reprocessamento da origem) — por isso removemos duplicatas por id_produto aqui, e não
# na bronze. nome_produto vem às vezes com espaços sobrando (copiar/colar na origem), daí
# o trim. faixa_preco existe para permitir segmentação comercial sem repetir a regra de
# corte em cada consumidor da tabela.
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType


@dp.materialized_view(
    name="produtos",
    comment="Produtos deduplicados por id_produto, com faixa de preço.",
)
@dp.expect_all_or_fail(
    {
        "id_produto_preenchido": "id_produto IS NOT NULL",
        "preco_atual_positivo": "preco_atual > 0",
    }
)
def produtos():
    df = spark.read.table("bronze.produtos").dropDuplicates(["id_produto"])

    return df.select(
        "id_produto",
        F.trim(F.col("nome_produto")).alias("nome_produto"),
        "categoria",
        "marca",
        F.col("preco_atual").cast(DecimalType(10, 2)).alias("preco_atual"),
        "data_criacao",
        F.when(F.col("preco_atual") > 1000, F.lit("PREMIUM"))
        .when(F.col("preco_atual") > 500, F.lit("MEDIO"))
        .otherwise(F.lit("BASICO"))
        .alias("faixa_preco"),
    )
