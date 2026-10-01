-- Diretoria Comercial: quanto vendemos e quando (dia, hora, dia da semana, canal). Uma linha
-- por data x hora x canal_venda, para gráficos de série temporal sem precisar reagregar
-- silver.vendas toda vez. clientes_unicos é COUNT DISTINCT por linha: um mesmo cliente que
-- compra em horas ou canais diferentes aparece em mais de uma linha, então somar essa coluna
-- entre linhas conta gente duas vezes — para clientes únicos no período, usar
-- gold.clientes_segmentacao (uma linha por cliente).
CREATE OR REFRESH MATERIALIZED VIEW gold.vendas_temporais (
  data DATE COMMENT 'Data da venda (America/Sao_Paulo, sem hora).',
  dia_semana STRING COMMENT 'Dia da semana por extenso, em português (Domingo, Segunda, ..., Sábado).',
  dia_semana_num INT COMMENT 'Dia da semana numérico: 1 = domingo, ..., 7 = sábado.',
  hora INT COMMENT 'Hora da venda (0 a 23).',
  canal_venda STRING COMMENT 'Canal da venda: ecommerce ou loja_fisica.',
  total_vendas BIGINT COMMENT 'Quantidade de vendas (linhas de silver.vendas) na combinação data x hora x canal_venda.',
  itens_vendidos BIGINT COMMENT 'Soma da quantidade de itens vendidos na combinação data x hora x canal_venda.',
  receita DECIMAL(10, 2) COMMENT 'Receita total em R$ na combinação data x hora x canal_venda (soma de quantidade x preco_unitario).',
  clientes_unicos BIGINT COMMENT 'Quantidade de clientes distintos (COUNT DISTINCT id_cliente) na combinação data x hora x canal_venda. NÃO some esta coluna entre linhas: o mesmo cliente pode aparecer em várias combinações e seria contado mais de uma vez. Para clientes únicos no período inteiro, use gold.clientes_segmentacao.'
)
COMMENT 'Vendas agregadas por data, hora e canal, para análises de série temporal (quando vendemos, em qual canal). Período: 13/12/2025 a 11/01/2026. Não use clientes_unicos para totalizar clientes no período — veja o comentário da coluna.'
AS
SELECT
  data,
  dia_semana,
  dia_semana_num,
  hora,
  canal_venda,
  COUNT(*) AS total_vendas,
  SUM(quantidade) AS itens_vendidos,
  CAST(SUM(receita) AS DECIMAL(10, 2)) AS receita,
  COUNT(DISTINCT id_cliente) AS clientes_unicos
FROM silver.vendas
GROUP BY data, dia_semana, dia_semana_num, hora, canal_venda
