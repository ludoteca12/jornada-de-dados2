-- Diretoria Comercial: com quais produtos vendemos. Uma linha por id_produto que aparece em
-- silver.vendas (LEFT JOIN com silver.produtos), porque uma venda de produto não cadastrado
-- ainda é receita e precisa aparecer aqui — ela só não tem nome_produto/categoria/marca/
-- faixa_preco reais, e por isso ganha os valores "Produto não cadastrado" / "Não cadastrado".
-- nome_produto não é chave: cadastros diferentes podem usar o mesmo nome de produto, então
-- todo agrupamento e ranking aqui é por id_produto, nunca por nome.
CREATE OR REFRESH MATERIALIZED VIEW gold.vendas_produtos (
  id_produto STRING COMMENT 'Identificador único do produto vendido.',
  nome_produto STRING COMMENT 'Nome do produto. "Produto não cadastrado" quando o id_produto da venda não existe em silver.produtos — produtos diferentes podem compartilhar o mesmo nome, então nunca agrupe ou identifique um produto pelo nome, sempre por id_produto.',
  categoria STRING COMMENT 'Categoria do produto. "Não cadastrado" quando o produto não existe em silver.produtos.',
  marca STRING COMMENT 'Marca do produto. "Não cadastrado" quando o produto não existe em silver.produtos.',
  faixa_preco STRING COMMENT 'Faixa de preço do produto (PREMIUM, MEDIO ou BASICO), de silver.produtos. NULL quando o produto não está cadastrado — não há preco_atual para calcular a faixa.',
  produto_cadastrado BOOLEAN COMMENT 'true quando o id_produto existe em silver.produtos, false quando a venda referencia um produto sem cadastro.',
  total_vendas BIGINT COMMENT 'Quantidade de vendas (linhas de silver.vendas) deste produto.',
  itens_vendidos BIGINT COMMENT 'Soma da quantidade de itens vendidos deste produto.',
  receita DECIMAL(10, 2) COMMENT 'Receita total em R$ deste produto (soma de quantidade x preco_unitario de todas as vendas, inclusive se o produto não está cadastrado).',
  ticket_medio DECIMAL(10, 2) COMMENT 'Receita média em R$ por venda deste produto (média da receita de cada venda, não receita total / total_vendas de outro produto).',
  ranking_receita INT COMMENT 'Posição do produto por receita entre TODOS os produtos, do maior para o menor (1 = maior receita).',
  ranking_na_categoria INT COMMENT 'Posição do produto por receita dentro da própria categoria (1 = maior receita na categoria). Produtos não cadastrados formam a categoria "Não cadastrado" e são ranqueados entre si.'
)
COMMENT 'Vendas agregadas por produto, com dados de cadastro e ranking de receita geral e por categoria. Use para responder "quais produtos mais vendem/faturam" e "quais produtos não estão cadastrados corretamente". Período: 13/12/2025 a 11/01/2026.'
AS
WITH vendas_com_produto AS (
  SELECT
    v.id_produto,
    COALESCE(p.nome_produto, 'Produto não cadastrado') AS nome_produto,
    COALESCE(p.categoria, 'Não cadastrado') AS categoria,
    COALESCE(p.marca, 'Não cadastrado') AS marca,
    p.faixa_preco,
    p.id_produto IS NOT NULL AS produto_cadastrado,
    v.quantidade,
    v.receita
  FROM silver.vendas v
  LEFT JOIN silver.produtos p ON v.id_produto = p.id_produto
),
agregado AS (
  SELECT
    id_produto,
    nome_produto,
    categoria,
    marca,
    faixa_preco,
    produto_cadastrado,
    COUNT(*) AS total_vendas,
    SUM(quantidade) AS itens_vendidos,
    CAST(SUM(receita) AS DECIMAL(10, 2)) AS receita,
    CAST(ROUND(AVG(receita), 2) AS DECIMAL(10, 2)) AS ticket_medio
  FROM vendas_com_produto
  GROUP BY id_produto, nome_produto, categoria, marca, faixa_preco, produto_cadastrado
)
SELECT
  id_produto,
  nome_produto,
  categoria,
  marca,
  faixa_preco,
  produto_cadastrado,
  total_vendas,
  itens_vendidos,
  receita,
  ticket_medio,
  ROW_NUMBER() OVER (ORDER BY receita DESC) AS ranking_receita,
  ROW_NUMBER() OVER (PARTITION BY categoria ORDER BY receita DESC) AS ranking_na_categoria
FROM agregado
