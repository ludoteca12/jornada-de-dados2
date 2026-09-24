-- Diretoria de Pricing: estamos mais caros que a concorrência, e em quais produtos agir? Uma
-- linha por id_produto (todo produto cadastrado tem pelo menos uma coleta de concorrente).
-- Preço suspeito é erro de coleta ou promoção pontual do concorrente — o diretor não pode
-- reagir a ele. Por isso classificacao_preco (o rótulo que aparece no dashboard) usa TODAS as
-- coletas, inclusive as suspeitas, porque uma coleta suspeita ainda é o que está no mercado e
-- o diretor precisa VER que ficamos "mais caros que todos" por causa dela; já
-- preco_medio_concorrentes, preco_minimo_concorrentes e diferenca_pct usam só coletas
-- confiáveis (NOT preco_suspeito), para não distorcer a régua de comparação de preço com um
-- valor de coleta ruim. possui_preco_suspeito é o flag que separa, no dashboard, o que é
-- confirmado do que precisa ser conferido antes de agir.
CREATE OR REFRESH MATERIALIZED VIEW gold.precos_competitividade (
  id_produto STRING COMMENT 'Identificador único do produto monitorado.',
  nome_produto STRING COMMENT 'Nome do produto.',
  categoria STRING COMMENT 'Categoria do produto.',
  marca STRING COMMENT 'Marca do produto.',
  nosso_preco DECIMAL(10, 2) COMMENT 'Nosso preço atual em R$ (preco_atual de silver.produtos).',
  preco_medio_concorrentes DECIMAL(10, 2) COMMENT 'Preço médio em R$ dos concorrentes, considerando só coletas NÃO suspeitas. NULL quando o produto não tem nenhuma coleta confiável (todas as coletas dele são suspeitas).',
  preco_minimo_concorrentes DECIMAL(10, 2) COMMENT 'Menor preço em R$ entre os concorrentes, considerando só coletas NÃO suspeitas. NULL quando o produto não tem nenhuma coleta confiável.',
  diferenca_pct DECIMAL(10, 2) COMMENT 'Diferença percentual entre nosso_preco e preco_medio_concorrentes: (nosso_preco - preco_medio_concorrentes) / preco_medio_concorrentes x 100. Valor em PONTOS PERCENTUAIS (10 = 10% mais caro que o mercado), não no formato 0-1. NULL quando preco_medio_concorrentes é NULL.',
  possui_preco_suspeito BOOLEAN COMMENT 'true quando pelo menos uma coleta de concorrente deste produto está marcada como suspeita (preco_suspeito em silver.preco_competidores) — indica que o preço precisa ser conferido antes de qualquer ação comercial.',
  classificacao_preco STRING COMMENT 'MAIS_CARO_QUE_TODOS quando nosso_preco é maior que o preço de TODOS os concorrentes (inclusive coletas suspeitas); MAIS_BARATO_QUE_TODOS quando é menor que o de todos; PRECO_COMPETITIVO nos demais casos. Cruze com possui_preco_suspeito antes de agir: um MAIS_CARO_QUE_TODOS com possui_preco_suspeito = true pode ser só erro de coleta.'
)
COMMENT 'Uma linha por produto monitorado, comparando nosso preço com a concorrência. Use para responder "estamos mais caros que o mercado, e onde agir". Separe sempre confirmado (possui_preco_suspeito = false) de suspeito (= true) antes de recomendar qualquer ação de preço — preço suspeito é erro de coleta ou promoção do concorrente. Período: 13/12/2025 a 11/01/2026.'
AS
WITH concorrentes_confirmados AS (
  SELECT
    id_produto,
    AVG(preco_concorrente) AS preco_medio_concorrentes,
    MIN(preco_concorrente) AS preco_minimo_concorrentes
  FROM silver.preco_competidores
  WHERE NOT preco_suspeito
  GROUP BY id_produto
),
concorrentes_todos AS (
  SELECT
    id_produto,
    MIN(preco_concorrente) AS preco_minimo_todos,
    MAX(preco_concorrente) AS preco_maximo_todos,
    MAX(CASE WHEN preco_suspeito THEN 1 ELSE 0 END) = 1 AS possui_preco_suspeito
  FROM silver.preco_competidores
  GROUP BY id_produto
)
SELECT
  p.id_produto,
  p.nome_produto,
  p.categoria,
  p.marca,
  p.preco_atual AS nosso_preco,
  CAST(cc.preco_medio_concorrentes AS DECIMAL(10, 2)) AS preco_medio_concorrentes,
  cc.preco_minimo_concorrentes,
  CAST(
    ROUND(
      (p.preco_atual - cc.preco_medio_concorrentes) / cc.preco_medio_concorrentes * 100,
      2
    ) AS DECIMAL(10, 2)
  ) AS diferenca_pct,
  ct.possui_preco_suspeito,
  CASE
    WHEN p.preco_atual > ct.preco_maximo_todos THEN 'MAIS_CARO_QUE_TODOS'
    WHEN p.preco_atual < ct.preco_minimo_todos THEN 'MAIS_BARATO_QUE_TODOS'
    ELSE 'PRECO_COMPETITIVO'
  END AS classificacao_preco
FROM silver.produtos p
JOIN concorrentes_todos ct ON p.id_produto = ct.id_produto
LEFT JOIN concorrentes_confirmados cc ON p.id_produto = cc.id_produto
