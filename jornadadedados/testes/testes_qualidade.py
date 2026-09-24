# Databricks notebook source
# Roda depois do pipeline silver. Cada teste é uma query de contagem — se achar problema,
# o notebook mostra uma tabela com o resultado de todos os testes e falha com
# AssertionError, para o Job "Pipeline E-commerce" parar e alertar antes que os dados
# ruins cheguem na gold.

# COMMAND ----------
dbutils.widgets.text("catalogo", "jornada-de-dados")
catalogo = dbutils.widgets.get("catalogo")


def tabela(nome):
    return f"`{catalogo}`.{nome}"


# COMMAND ----------
from pyspark.sql import functions as F

resultados = []


def registrar(nome_teste, linhas_com_problema):
    resultados.append({"teste": nome_teste, "linhas_com_problema": linhas_com_problema})


# COMMAND ----------
# Chaves únicas das 4 silver

chaves = {
    "silver.produtos": ["id_produto"],
    "silver.clientes": ["id_cliente"],
    "silver.preco_competidores": ["id_produto", "nome_concorrente"],
    "silver.vendas": ["id_venda"],
}

for nome_tabela, chave in chaves.items():
    df = spark.read.table(tabela(nome_tabela))
    duplicatas = df.count() - df.dropDuplicates(chave).count()
    registrar(f"chave_unica_{nome_tabela}", duplicatas)

# COMMAND ----------
# receita = quantidade * preco_unitario em silver.vendas

vendas = spark.read.table(tabela("silver.vendas"))
receita_incorreta = vendas.where(
    F.col("receita") != (F.col("quantidade") * F.col("preco_unitario"))
).count()
registrar("receita_igual_quantidade_x_preco_unitario", receita_incorreta)

# COMMAND ----------
# Vendas de produto não cadastrado devem ficar abaixo de 1% do total

total_vendas = vendas.count()
vendas_nao_cadastrado = vendas.where(~F.col("produto_cadastrado")).count()
percentual = (vendas_nao_cadastrado / total_vendas) if total_vendas else 0
registrar(
    "vendas_produto_nao_cadastrado_abaixo_de_1pct",
    0 if percentual < 0.01 else vendas_nao_cadastrado,
)

# COMMAND ----------
resultado_df = spark.createDataFrame(resultados)
display(resultado_df)

testes_com_falha = [r for r in resultados if r["linhas_com_problema"] > 0]
if testes_com_falha:
    raise AssertionError(f"Testes de qualidade falharam: {testes_com_falha}")
