# Cadastro manual permite o mesmo cliente duas vezes (reenvio de formulário) e nomes
# digitados com pronome de tratamento na frente (Sr., Sra., Srta., Dr., Dra.) e
# capitalização inconsistente — guardamos nome_original para auditoria e normalizamos
# nome_cliente separadamente. Não existe tabela de UF->região na bronze, então o
# mapeamento das 27 UFs (fonte: divisão regional do IBGE) é fixo aqui.
from pyspark import pipelines as dp
from pyspark.sql import functions as F

UF_PARA_REGIAO = {
    # Norte
    "AC": ("Acre", "Norte"),
    "AP": ("Amapa", "Norte"),
    "AM": ("Amazonas", "Norte"),
    "PA": ("Para", "Norte"),
    "RO": ("Rondonia", "Norte"),
    "RR": ("Roraima", "Norte"),
    "TO": ("Tocantins", "Norte"),
    # Nordeste
    "AL": ("Alagoas", "Nordeste"),
    "BA": ("Bahia", "Nordeste"),
    "CE": ("Ceara", "Nordeste"),
    "MA": ("Maranhao", "Nordeste"),
    "PB": ("Paraiba", "Nordeste"),
    "PE": ("Pernambuco", "Nordeste"),
    "PI": ("Piaui", "Nordeste"),
    "RN": ("Rio Grande do Norte", "Nordeste"),
    "SE": ("Sergipe", "Nordeste"),
    # Centro-Oeste
    "DF": ("Distrito Federal", "Centro-Oeste"),
    "GO": ("Goias", "Centro-Oeste"),
    "MT": ("Mato Grosso", "Centro-Oeste"),
    "MS": ("Mato Grosso do Sul", "Centro-Oeste"),
    # Sudeste
    "ES": ("Espirito Santo", "Sudeste"),
    "MG": ("Minas Gerais", "Sudeste"),
    "RJ": ("Rio de Janeiro", "Sudeste"),
    "SP": ("Sao Paulo", "Sudeste"),
    # Sul
    "PR": ("Parana", "Sul"),
    "RS": ("Rio Grande do Sul", "Sul"),
    "SC": ("Santa Catarina", "Sul"),
}

_MAPA_ESTADO = F.create_map(
    *[item for uf, (nome, _) in UF_PARA_REGIAO.items() for item in (F.lit(uf), F.lit(nome))]
)
_MAPA_REGIAO = F.create_map(
    *[item for uf, (_, regiao) in UF_PARA_REGIAO.items() for item in (F.lit(uf), F.lit(regiao))]
)

PADRAO_PRONOME = r"^(Sr\.|Sra\.|Srta\.|Dr\.|Dra\.)\s+"


@dp.materialized_view(
    name="clientes",
    comment="Clientes deduplicados por id_cliente, nome normalizado e região a partir da UF.",
)
@dp.expect_all_or_fail(
    {
        "id_cliente_preenchido": "id_cliente IS NOT NULL",
        "regiao_preenchida": "regiao IS NOT NULL",
    }
)
def clientes():
    df = spark.read.table("bronze.clientes").dropDuplicates(["id_cliente"])
    estado = F.upper(F.trim(F.col("estado")))

    return df.select(
        "id_cliente",
        F.col("nome_cliente").alias("nome_original"),
        F.initcap(
            F.trim(F.regexp_replace(F.col("nome_cliente"), PADRAO_PRONOME, ""))
        ).alias("nome_cliente"),
        estado.alias("estado"),
        "pais",
        "data_cadastro",
        _MAPA_ESTADO.getItem(estado).alias("nome_estado"),
        _MAPA_REGIAO.getItem(estado).alias("regiao"),
    )
