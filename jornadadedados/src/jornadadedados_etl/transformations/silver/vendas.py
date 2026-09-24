# O checkout permite reenviar a mesma venda em caso de timeout, daí a dedup por
# id_venda. produto_cadastrado e venda_antes_do_cadastro existem porque a venda e o
# cadastro do produto vêm de sistemas diferentes que às vezes dessincronizam — nunca
# descartamos essas vendas (impactaria a receita), só marcamos para análise.
# dayofweek do Spark já retorna 1=domingo...7=sábado, igual ao pedido, então não
# precisamos reindexar o dia da semana.
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

DIA_SEMANA_PT = {
    1: "Domingo",
    2: "Segunda",
    3: "Terca",
    4: "Quarta",
    5: "Quinta",
    6: "Sexta",
    7: "Sabado",
}
_MAPA_DIA_SEMANA = F.create_map(
    *[item for num, nome in DIA_SEMANA_PT.items() for item in (F.lit(num), F.lit(nome))]
)


@dp.materialized_view(
    name="vendas",
    comment="Vendas deduplicadas por id_venda, com receita, decomposição de data e cruzamento com produtos.",
)
@dp.expect_all_or_fail(
    {
        "id_venda_preenchido": "id_venda IS NOT NULL",
        "data_venda_preenchida": "data_venda IS NOT NULL",
        "id_cliente_preenchido": "id_cliente IS NOT NULL",
        "id_produto_preenchido": "id_produto IS NOT NULL",
        "quantidade_preenchida": "quantidade IS NOT NULL",
        "preco_unitario_preenchido": "preco_unitario IS NOT NULL",
        "quantidade_positiva": "quantidade > 0",
        "preco_unitario_positivo": "preco_unitario > 0",
        "canal_venda_valido": "canal_venda IN ('ecommerce', 'loja_fisica')",
    }
)
@dp.expect("produto_cadastrado", "produto_cadastrado")
@dp.expect("venda_depois_do_cadastro", "venda_depois_do_cadastro")
def vendas():
    bronze = spark.read.table("bronze.vendas").dropDuplicates(["id_venda"])
    produtos = spark.read.table("silver.produtos").select(
        "id_produto", F.col("data_criacao").alias("_data_criacao_produto")
    )

    df = bronze.join(produtos, "id_produto", "left")

    preco_unitario = F.col("preco_unitario").cast(DecimalType(10, 2))
    receita = (F.col("quantidade") * preco_unitario).cast(DecimalType(10, 2))
    produto_cadastrado = F.col("_data_criacao_produto").isNotNull()
    venda_antes_do_cadastro = produto_cadastrado & (
        F.col("data_venda") < F.col("_data_criacao_produto")
    )
    dia_semana_num = F.dayofweek(F.col("data_venda"))

    return df.select(
        "id_venda",
        "data_venda",
        "id_cliente",
        "id_produto",
        "canal_venda",
        "quantidade",
        preco_unitario.alias("preco_unitario"),
        receita.alias("receita"),
        F.to_date(F.col("data_venda")).alias("data"),
        F.hour(F.col("data_venda")).alias("hora"),
        dia_semana_num.alias("dia_semana_num"),
        _MAPA_DIA_SEMANA.getItem(dia_semana_num).alias("dia_semana"),
        produto_cadastrado.alias("produto_cadastrado"),
        F.coalesce(venda_antes_do_cadastro, F.lit(False)).alias("venda_antes_do_cadastro"),
        (~F.coalesce(venda_antes_do_cadastro, F.lit(False))).alias("venda_depois_do_cadastro"),
    )
