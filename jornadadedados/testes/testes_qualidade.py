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
    "gold.vendas_detalhadas": ["id_venda"],
    "gold.precos_competitividade": ["id_produto"],
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
# gold.clientes_segmentacao: receita total deve bater com silver.vendas

clientes_segmentacao = spark.read.table(tabela("gold.clientes_segmentacao"))
receita_gold = clientes_segmentacao.agg(F.sum("receita")).first()[0] or 0
receita_silver = vendas.agg(F.sum("receita")).first()[0] or 0
registrar(
    "gold_clientes_segmentacao_receita_igual_silver_vendas",
    0 if receita_gold == receita_silver else 1,
)

# COMMAND ----------
# gold.clientes_segmentacao: id_cliente único

duplicatas_gold_clientes = (
    clientes_segmentacao.count()
    - clientes_segmentacao.dropDuplicates(["id_cliente"]).count()
)
registrar("gold_clientes_segmentacao_id_cliente_unico", duplicatas_gold_clientes)

# COMMAND ----------
# gold.clientes_segmentacao: segmento só pode ser VIP, TOP_TIER ou REGULAR, e nenhum VIP
# com receita abaixo de 22.000

segmento_invalido = clientes_segmentacao.where(
    ~F.col("segmento_cliente").isin("VIP", "TOP_TIER", "REGULAR")
).count()
registrar("gold_clientes_segmentacao_segmento_valido", segmento_invalido)

vip_abaixo_do_limite = clientes_segmentacao.where(
    (F.col("segmento_cliente") == "VIP") & (F.col("receita") < 22000)
).count()
registrar("gold_clientes_segmentacao_vip_acima_de_22000", vip_abaixo_do_limite)

# COMMAND ----------
# gold.vendas_temporais, gold.vendas_produtos e gold.vendas_detalhadas: receita total deve
# bater com silver.vendas (nenhuma venda pode se perder ou duplicar nas agregações)

for nome_tabela in ("gold.vendas_temporais", "gold.vendas_produtos", "gold.vendas_detalhadas"):
    receita_tabela = spark.read.table(tabela(nome_tabela)).agg(F.sum("receita")).first()[0] or 0
    registrar(
        f"{nome_tabela}_receita_igual_silver_vendas".replace(".", "_"),
        0 if receita_tabela == receita_silver else 1,
    )

# COMMAND ----------
# gold.vendas_detalhadas: mesmo número de linhas de silver.vendas (grão de uma linha por venda)

vendas_detalhadas = spark.read.table(tabela("gold.vendas_detalhadas"))
diferenca_linhas = abs(vendas_detalhadas.count() - total_vendas)
registrar("gold_vendas_detalhadas_mesma_contagem_de_silver_vendas", diferenca_linhas)

# COMMAND ----------
# gold.vendas_detalhadas: toda venda precisa ter segmento e região preenchidos (o join com
# gold.clientes_segmentacao não pode perder nenhuma venda)

sem_segmento_ou_regiao = vendas_detalhadas.where(
    F.col("segmento_cliente").isNull() | F.col("regiao").isNull()
).count()
registrar("gold_vendas_detalhadas_toda_venda_com_segmento_e_regiao", sem_segmento_ou_regiao)

# COMMAND ----------
# gold.precos_competitividade: id_produto único (teste pedido no prompt_04), uma linha por
# produto monitorado (mesma contagem de silver.produtos), classificacao_preco só nos 5
# valores válidos, e preco_medio/minimo/maximo_concorrentes sempre preenchidos (produto com
# preço suspeito continua em todas as contas, nunca vira NULL)

precos_competitividade = spark.read.table(tabela("gold.precos_competitividade"))
total_produtos = spark.read.table(tabela("silver.produtos")).count()
registrar(
    "gold_precos_competitividade_mesma_contagem_de_silver_produtos",
    abs(precos_competitividade.count() - total_produtos),
)

classificacao_invalida = precos_competitividade.where(
    ~F.col("classificacao_preco").isin(
        "MAIS_CARO_QUE_TODOS",
        "MAIS_BARATO_QUE_TODOS",
        "ACIMA_DA_MEDIA",
        "ABAIXO_DA_MEDIA",
        "NA_MEDIA",
    )
).count()
registrar("gold_precos_competitividade_classificacao_valida", classificacao_invalida)

diferenca_pct_inconsistente = precos_competitividade.where(
    F.col("preco_medio_concorrentes").isNull()
    | F.col("preco_minimo_concorrentes").isNull()
    | F.col("preco_maximo_concorrentes").isNull()
).count()
registrar(
    "gold_precos_competitividade_precos_concorrentes_sempre_preenchidos",
    diferenca_pct_inconsistente,
)

# COMMAND ----------
# Toda coluna das tabelas gold precisa ter comentário (Genie e dashboard dependem disso).
# Ignora tabelas __materialization_*, que são internas do pipeline.

gold_tabelas = [
    r.tableName
    for r in spark.sql(f"SHOW TABLES IN {tabela('gold')}").collect()
    if not r.tableName.startswith("__materialization")
]
colunas_sem_comentario = []
for nome_tabela in gold_tabelas:
    colunas = spark.sql(f"DESCRIBE TABLE {tabela(f'gold.{nome_tabela}')}").collect()
    for c in colunas:
        if c.col_name and not c.col_name.startswith("#") and not c.comment:
            colunas_sem_comentario.append(f"{nome_tabela}.{c.col_name}")
registrar("gold_todas_as_colunas_com_comentario", len(colunas_sem_comentario))

# COMMAND ----------
resultado_df = spark.createDataFrame(resultados)
display(resultado_df)

testes_com_falha = [r for r in resultados if r["linhas_com_problema"] > 0]
if testes_com_falha:
    raise AssertionError(f"Testes de qualidade falharam: {testes_com_falha}")
