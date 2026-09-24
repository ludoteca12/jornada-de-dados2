-- Diretoria de Customer Success: quem são os melhores clientes, onde estão e como
-- segmentar a carteira. Uma linha por cliente, INCLUSIVE quem nunca comprou (LEFT JOIN a
-- partir de silver.clientes) — é justamente esse cliente sem receita que o time de CS
-- precisa ativar. Toda venda entra na receita, mesmo de produto não cadastrado: dinheiro
-- que entrou é receita, não é problema de cadastro.
--
-- Faixas de segmento definidas com a diretora a partir da distribuição real de receita por
-- cliente (período 13/12/2025 a 11/01/2026). As faixas antigas (VIP >= R$ 10.000,
-- TOP_TIER >= R$ 5.000) foram descartadas porque, com a base atual, quase todo mundo virava
-- VIP — não discriminavam os melhores clientes. As faixas novas (VIP >= R$ 22.000,
-- TOP_TIER >= R$ 17.000) foram calibradas para produzir uma pirâmide real: poucos VIP,
-- um grupo intermediário maior e a base em REGULAR.
CREATE OR REFRESH MATERIALIZED VIEW gold.clientes_segmentacao (
  id_cliente STRING COMMENT 'Identificador único do cliente.',
  nome_cliente STRING COMMENT 'Nome do cliente já sem pronome de tratamento (Sr., Sra., Srta., Dr., Dra.).',
  estado STRING COMMENT 'UF do cliente (sigla, maiúscula).',
  nome_estado STRING COMMENT 'Nome por extenso do estado, a partir da UF.',
  regiao STRING COMMENT 'Região do Brasil (Norte, Nordeste, Centro-Oeste, Sudeste, Sul), a partir da UF.',
  total_compras BIGINT COMMENT 'Quantidade de vendas do cliente no período. 0 para quem nunca comprou.',
  receita DECIMAL(10,2) COMMENT 'Receita total em R$ do cliente no período (soma de quantidade x preco_unitario de todas as vendas, inclusive de produto não cadastrado). 0,00 para quem nunca comprou.',
  ticket_medio DECIMAL(10,2) COMMENT 'Receita média em R$ por venda do cliente (receita total / total_compras). NULL para quem nunca comprou — não existe venda para tirar média.',
  primeira_compra DATE COMMENT 'Data da primeira venda do cliente. NULL para quem nunca comprou.',
  ultima_compra DATE COMMENT 'Data da última venda do cliente. NULL para quem nunca comprou.',
  segmento_cliente STRING COMMENT 'Segmento por receita: VIP (receita >= R$ 22.000,00), TOP_TIER (R$ 17.000,00 a R$ 21.999,99) ou REGULAR (abaixo de R$ 17.000,00). Quem nunca comprou entra em REGULAR.',
  ranking_receita INT COMMENT 'Posição do cliente por receita, do maior para o menor (1 = maior receita). Empates recebem posições distintas, em ordem arbitrária.',
  CONSTRAINT id_cliente_preenchido EXPECT (id_cliente IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT segmento_valido EXPECT (segmento_cliente IN ('VIP', 'TOP_TIER', 'REGULAR')) ON VIOLATION FAIL UPDATE
)
COMMENT 'Uma linha por cliente cadastrado (inclusive quem nunca comprou), com localização e segmento de receita. Use para identificar os melhores clientes (ranking_receita, segmento_cliente VIP), planejar ativação de carteira (receita = 0) e analisar a base por estado/região. Período: 13/12/2025 a 11/01/2026.'
AS
WITH vendas_cliente AS (
  SELECT
    id_cliente,
    COUNT(*) AS total_compras,
    SUM(receita) AS receita,
    MIN(data) AS primeira_compra,
    MAX(data) AS ultima_compra
  FROM silver.vendas
  GROUP BY id_cliente
)
SELECT
  c.id_cliente,
  c.nome_cliente,
  c.estado,
  c.nome_estado,
  c.regiao,
  COALESCE(v.total_compras, 0) AS total_compras,
  CAST(COALESCE(v.receita, 0) AS DECIMAL(10, 2)) AS receita,
  CAST(ROUND(v.receita / v.total_compras, 2) AS DECIMAL(10, 2)) AS ticket_medio,
  v.primeira_compra,
  v.ultima_compra,
  CASE
    WHEN COALESCE(v.receita, 0) >= 22000 THEN 'VIP'
    WHEN COALESCE(v.receita, 0) >= 17000 THEN 'TOP_TIER'
    ELSE 'REGULAR'
  END AS segmento_cliente,
  ROW_NUMBER() OVER (ORDER BY COALESCE(v.receita, 0) DESC) AS ranking_receita
FROM silver.clientes c
LEFT JOIN vendas_cliente v ON c.id_cliente = v.id_cliente
