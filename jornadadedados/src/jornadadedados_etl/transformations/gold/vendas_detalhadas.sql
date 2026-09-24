-- Uma linha por venda, com produto e cliente/segmento já resolvidos, para perguntas que
-- cruzam diretorias (ex.: receita por região e categoria, canal preferido dos clientes VIP) e
-- para os filtros cruzados de um dashboard único. É a tabela mais granular da gold: as outras
-- (vendas_temporais, vendas_produtos) agregam a partir daqui, então nunca perdem informação
-- que essa tabela também não tenha. CLUSTER BY (data) porque é a coluna mais usada para
-- filtrar/particionar consultas de série temporal.
CREATE OR REFRESH MATERIALIZED VIEW gold.vendas_detalhadas (
  id_venda STRING COMMENT 'Identificador único da venda.',
  data_venda TIMESTAMP COMMENT 'Data e hora completas da venda (UTC).',
  data DATE COMMENT 'Data da venda, sem hora.',
  dia_semana STRING COMMENT 'Dia da semana por extenso, em português (Domingo, Segunda, ..., Sábado).',
  dia_semana_num INT COMMENT 'Dia da semana numérico: 1 = domingo, ..., 7 = sábado.',
  hora INT COMMENT 'Hora da venda em UTC (0 a 23).',
  canal_venda STRING COMMENT 'Canal da venda: ecommerce ou loja_fisica.',
  id_produto STRING COMMENT 'Identificador do produto vendido.',
  nome_produto STRING COMMENT 'Nome do produto. "Produto não cadastrado" quando o id_produto não existe em silver.produtos — produtos diferentes podem compartilhar nome, agrupe sempre por id_produto.',
  categoria STRING COMMENT 'Categoria do produto. "Não cadastrado" quando o produto não existe em silver.produtos.',
  marca STRING COMMENT 'Marca do produto. "Não cadastrado" quando o produto não existe em silver.produtos.',
  faixa_preco STRING COMMENT 'Faixa de preço do produto (PREMIUM, MEDIO ou BASICO). NULL quando o produto não está cadastrado.',
  id_cliente STRING COMMENT 'Identificador do cliente que comprou.',
  nome_cliente STRING COMMENT 'Nome do cliente, já sem pronome de tratamento.',
  estado STRING COMMENT 'UF do cliente (sigla, maiúscula).',
  regiao STRING COMMENT 'Região do Brasil do cliente (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).',
  segmento_cliente STRING COMMENT 'Segmento de receita do cliente no período (VIP, TOP_TIER ou REGULAR), de gold.clientes_segmentacao — reflete a receita total do cliente, não desta venda isolada.',
  quantidade BIGINT COMMENT 'Quantidade de itens vendidos nesta venda.',
  preco_unitario DECIMAL(10, 2) COMMENT 'Preço unitário em R$ praticado nesta venda.',
  receita DECIMAL(10, 2) COMMENT 'Receita em R$ desta venda (quantidade x preco_unitario).',
  produto_cadastrado BOOLEAN COMMENT 'true quando o id_produto desta venda existe em silver.produtos.',
  venda_antes_do_cadastro BOOLEAN COMMENT 'true quando data_venda é anterior à data_criacao do produto (produto cadastrado depois da venda). false quando o produto não está cadastrado ou foi cadastrado antes da venda.'
)
CLUSTER BY (data)
COMMENT 'Uma linha por venda, já cruzada com produto e cliente/segmento/região. Use para perguntas que cruzam diretorias (receita por região e categoria, canal preferido dos VIPs) e para filtros que precisam valer em vários gráficos ao mesmo tempo. Período: 13/12/2025 a 11/01/2026.'
AS
SELECT
  v.id_venda,
  v.data_venda,
  v.data,
  v.dia_semana,
  v.dia_semana_num,
  v.hora,
  v.canal_venda,
  v.id_produto,
  COALESCE(p.nome_produto, 'Produto não cadastrado') AS nome_produto,
  COALESCE(p.categoria, 'Não cadastrado') AS categoria,
  COALESCE(p.marca, 'Não cadastrado') AS marca,
  p.faixa_preco,
  v.id_cliente,
  c.nome_cliente,
  c.estado,
  c.regiao,
  c.segmento_cliente,
  v.quantidade,
  v.preco_unitario,
  v.receita,
  v.produto_cadastrado,
  v.venda_antes_do_cadastro
FROM silver.vendas v
LEFT JOIN silver.produtos p ON v.id_produto = p.id_produto
LEFT JOIN gold.clientes_segmentacao c ON v.id_cliente = c.id_cliente
