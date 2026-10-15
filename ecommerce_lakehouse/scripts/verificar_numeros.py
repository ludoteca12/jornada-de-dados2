"""Confere os números de referência do projeto num catálogo (dev ou prod).

Uso:
    python scripts/verificar_numeros.py --profile <perfil> --catalogo ecommerce_lakehouse_dev

Sai com código 1 se algum número divergir. Os valores esperados correspondem aos arquivos de
`seed/`; se a origem mudar, eles mudam junto.
"""

import argparse
import sys

from _databricks import consultas


def verificacoes(c):
    s, g = f"{c}.silver", f"{c}.gold"
    return [
        ("Vendas na silver", f"SELECT COUNT(*) FROM {s}.vendas", "3020"),
        ("Receita total (R$)", f"SELECT SUM(receita) FROM {s}.vendas", "974077.28"),
        ("Vendas de produto não cadastrado", f"SELECT COUNT(*) FROM {s}.vendas WHERE NOT produto_cadastrado", "20"),
        ("Vendas antes do cadastro do produto", f"SELECT COUNT(*) FROM {s}.vendas WHERE venda_antes_do_cadastro", "5"),
        ("Preços de concorrente suspeitos", f"SELECT COUNT(*) FROM {s}.preco_competidores WHERE preco_suspeito", "55"),
        ("Clientes com pronome de tratamento", f"SELECT COUNT(*) FROM {s}.clientes WHERE nome_original RLIKE '^(Sr|Sra|Srta|Dr|Dra)\\\\.'", "11"),
        ("Receita gold = silver (vendas_detalhadas)", f"SELECT SUM(receita) FROM {g}.vendas_detalhadas", "974077.28"),
        ("Ticket médio (R$)", f"SELECT ROUND(SUM(receita) / COUNT(*), 2) FROM {g}.vendas_detalhadas", "322.54"),
        ("Vendas no e-commerce", f"SELECT COUNT(*) FROM {g}.vendas_detalhadas WHERE canal_venda = 'ecommerce'", "2155"),
        ("Clientes", f"SELECT COUNT(*) FROM {g}.clientes_segmentacao", "50"),
        ("Clientes VIP", f"SELECT COUNT(*) FROM {g}.clientes_segmentacao WHERE segmento_cliente = 'VIP'", "10"),
        ("% da receita vinda de VIP", f"SELECT ROUND(100 * SUM(CASE WHEN segmento_cliente = 'VIP' THEN receita ELSE 0 END) / SUM(receita), 1) FROM {g}.clientes_segmentacao", "27.0"),
        ("Região de maior receita", f"SELECT regiao FROM {g}.clientes_segmentacao GROUP BY regiao ORDER BY SUM(receita) DESC LIMIT 1", "Norte"),
        ("Produtos monitorados", f"SELECT COUNT(*) FROM {g}.precos_competitividade", "215"),
        ("Mais caros que todos os concorrentes", f"SELECT COUNT(*) FROM {g}.precos_competitividade WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'", "35"),
        ("... confirmados (sem preço suspeito)", f"SELECT COUNT(*) FROM {g}.precos_competitividade WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS' AND NOT possui_preco_suspeito", "20"),
        ("Receita dos confirmados (R$)", f"SELECT SUM(receita) FROM {g}.precos_competitividade WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS' AND NOT possui_preco_suspeito", "161375.09"),
        ("Produtos com preço suspeito", f"SELECT COUNT(*) FROM {g}.precos_competitividade WHERE possui_preco_suspeito", "15"),
        ("Categoria mais cara sem suspeitos", f"SELECT categoria FROM {g}.precos_competitividade WHERE NOT possui_preco_suspeito GROUP BY categoria ORDER BY AVG(diferenca_pct_vs_media) DESC LIMIT 1", "Beleza"),
    ]


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--profile", required=True)
    p.add_argument("--catalogo", default="ecommerce_lakehouse_dev")
    a = p.parse_args()

    itens = verificacoes(a.catalogo)
    resultados = consultas([sql for _, sql, _ in itens], profile=a.profile)

    falhas = 0
    print(f"Catálogo: {a.catalogo}\n")
    for (nome, _, esperado), linhas in zip(itens, resultados):
        obtido = f"ERRO: {linhas}" if isinstance(linhas, Exception) else (linhas[0][0] if linhas else "(vazio)")
        ok = obtido == esperado
        falhas += not ok
        print(f"  {'OK  ' if ok else 'FALHA'}  {nome:<42} esperado {esperado:>10}   obtido {obtido}")

    print(f"\n{len(itens) - falhas}/{len(itens)} números de referência conferem.")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
