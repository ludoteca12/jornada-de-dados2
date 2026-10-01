-- Diretoria de Pricing: estamos mais caros que a concorrência (Mercado Livre, Amazon, Magalu
-- e Shopee), e em quais produtos agir? Uma linha por produto que tem pelo menos uma coleta de
-- preço de concorrente (JOIN de silver.produtos com a agregação de silver.preco_competidores;
-- LEFT JOIN com a receita de silver.vendas).
--
-- Produto com preço suspeito CONTINUA em todas as contas (média, mínimo, máximo,
-- classificação): promoção relâmpago do concorrente existe de verdade, e descartar a coleta
-- jogaria fora um preço de mercado real. possui_preco_suspeito só ALERTA que esse preço
-- precisa ser confirmado manualmente antes de qualquer ação comercial — nunca filtra o
-- cálculo. É por isso que produtos cuja única coleta é suspeita (ex.: a categoria Tênis nesta
-- base) aparecem com diferença extrema: o número é real dado o que foi coletado, só não é
-- confiável até alguém confirmar.
CREATE OR REFRESH MATERIALIZED VIEW gold.precos_competitividade (
  id_produto STRING COMMENT 'Identificador único do produto monitorado.',
  nome_produto STRING COMMENT 'Nome do produto.',
  categoria STRING COMMENT 'Categoria do produto.',
  marca STRING COMMENT 'Marca do produto.',
  nosso_preco DECIMAL(10, 2) COMMENT 'Nosso preço atual em R$ (preco_atual de silver.produtos).',
  preco_medio_concorrentes DECIMAL(10, 2) COMMENT 'Preço médio em R$ entre os concorrentes (Mercado Livre, Amazon, Magalu, Shopee), considerando TODAS as coletas, inclusive as suspeitas — veja possui_preco_suspeito.',
  preco_minimo_concorrentes DECIMAL(10, 2) COMMENT 'Menor preço em R$ entre os concorrentes, considerando todas as coletas.',
  preco_maximo_concorrentes DECIMAL(10, 2) COMMENT 'Maior preço em R$ entre os concorrentes, considerando todas as coletas.',
  total_concorrentes BIGINT COMMENT 'Quantidade de coletas de preço de concorrente para este produto (até 4: Mercado Livre, Amazon, Magalu, Shopee).',
  diferenca_pct_vs_media DECIMAL(10, 2) COMMENT 'Diferença percentual entre nosso_preco e preco_medio_concorrentes: (nosso_preco - preco_medio_concorrentes) / preco_medio_concorrentes x 100. Valor em PONTOS PERCENTUAIS (10 = 10% mais caro que a média do mercado), não no formato 0-1.',
  diferenca_pct_vs_minimo DECIMAL(10, 2) COMMENT 'Diferença percentual entre nosso_preco e preco_minimo_concorrentes: (nosso_preco - preco_minimo_concorrentes) / preco_minimo_concorrentes x 100. Valor em PONTOS PERCENTUAIS (10 = 10% mais caro que o concorrente mais barato), não no formato 0-1.',
  classificacao_preco STRING COMMENT 'MAIS_CARO_QUE_TODOS quando nosso_preco é maior que o preço de TODOS os concorrentes; MAIS_BARATO_QUE_TODOS quando é menor que o de todos; caso contrário, compara com a média: ACIMA_DA_MEDIA, ABAIXO_DA_MEDIA ou NA_MEDIA (igual à média). Cruze sempre com possui_preco_suspeito antes de agir: um MAIS_CARO_QUE_TODOS com possui_preco_suspeito = true pode ser só uma promoção pontual do concorrente, não um problema de preço real.',
  possui_preco_suspeito BOOLEAN COMMENT 'true quando pelo menos uma coleta de concorrente deste produto está marcada como suspeita (preco_suspeito em silver.preco_competidores — preço abaixo de 60% do nosso). O produto continua em todas as contas desta tabela; esta coluna só avisa que o preço precisa ser conferido manualmente (erro de coleta ou promoção relâmpago) antes de qualquer ação comercial.',
  receita DECIMAL(10, 2) COMMENT 'Receita total em R$ deste produto no período (soma de quantidade x preco_unitario de todas as vendas). 0,00 quando o produto nunca foi vendido.',
  itens_vendidos BIGINT COMMENT 'Soma da quantidade de itens vendidos deste produto no período. 0 quando o produto nunca foi vendido.'
)
COMMENT 'Uma linha por produto monitorado, comparando nosso preço com a concorrência (Mercado Livre, Amazon, Magalu, Shopee). Use para responder "estamos mais caros que o mercado, e onde agir". Preço suspeito (possui_preco_suspeito) é erro de coleta ou promoção relâmpago do concorrente — o produto continua em todas as contas desta tabela, mas o diretor não deve reagir sem antes confirmar manualmente. Período: 13/12/2025 a 11/01/2026.'
AS
WITH concorrentes AS (
  SELECT
    id_produto,
    CAST(ROUND(AVG(preco_concorrente), 2) AS DECIMAL(10, 2)) AS preco_medio_concorrentes,
    MIN(preco_concorrente) AS preco_minimo_concorrentes,
    MAX(preco_concorrente) AS preco_maximo_concorrentes,
    COUNT(*) AS total_concorrentes,
    MAX(CASE WHEN preco_suspeito THEN 1 ELSE 0 END) = 1 AS possui_preco_suspeito
  FROM silver.preco_competidores
  GROUP BY id_produto
),
vendas_produto AS (
  SELECT id_produto, SUM(receita) AS receita, SUM(quantidade) AS itens_vendidos
  FROM silver.vendas
  GROUP BY id_produto
)
SELECT
  p.id_produto,
  p.nome_produto,
  p.categoria,
  p.marca,
  p.preco_atual AS nosso_preco,
  c.preco_medio_concorrentes,
  c.preco_minimo_concorrentes,
  c.preco_maximo_concorrentes,
  c.total_concorrentes,
  CAST(
    ROUND((p.preco_atual - c.preco_medio_concorrentes) / c.preco_medio_concorrentes * 100, 2)
    AS DECIMAL(10, 2)
  ) AS diferenca_pct_vs_media,
  CAST(
    ROUND((p.preco_atual - c.preco_minimo_concorrentes) / c.preco_minimo_concorrentes * 100, 2)
    AS DECIMAL(10, 2)
  ) AS diferenca_pct_vs_minimo,
  CASE
    WHEN p.preco_atual > c.preco_maximo_concorrentes THEN 'MAIS_CARO_QUE_TODOS'
    WHEN p.preco_atual < c.preco_minimo_concorrentes THEN 'MAIS_BARATO_QUE_TODOS'
    WHEN p.preco_atual > c.preco_medio_concorrentes THEN 'ACIMA_DA_MEDIA'
    WHEN p.preco_atual < c.preco_medio_concorrentes THEN 'ABAIXO_DA_MEDIA'
    ELSE 'NA_MEDIA'
  END AS classificacao_preco,
  c.possui_preco_suspeito,
  CAST(COALESCE(v.receita, 0) AS DECIMAL(10, 2)) AS receita,
  COALESCE(v.itens_vendidos, 0) AS itens_vendidos
FROM silver.produtos p
JOIN concorrentes c ON p.id_produto = c.id_produto
LEFT JOIN vendas_produto v ON p.id_produto = v.id_produto
