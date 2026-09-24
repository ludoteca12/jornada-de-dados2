# Prompt 1: um dashboard para cada diretor

A gold da Aula 3 está pronta e agora vira produto para os três diretores: um dashboard AI/BI para
cada diretoria, como código dentro deste bundle. Use o perfil de CLI e o catálogo do CLAUDE.md
(catálogo projetoaovivo) e o warehouse "Serverless Starter Warehouse".

CONTEXTO
- As tabelas já existem em projetoaovivo.gold: vendas_temporais, vendas_produtos, vendas_detalhadas,
  clientes_segmentacao e precos_competitividade. Os comentários de cada coluna explicam unidade e
  regra de cálculo: leia antes de montar qualquer gráfico.
- Período dos dados: 13/12/2025 a 11/01/2026. Nada de current_date().
- Antes de escrever o JSON, explore as tabelas (cardinalidade, valores, distribuição) e teste no
  warehouse TODAS as consultas que vão virar dataset. Me mostre os números dos KPIs antes do deploy.

CONVENÇÕES (grave nas instruções do projeto: o CLAUDE.md, ou o AGENTS.md que ele importa)
- Um arquivo por dashboard: src/dashboards/<nome>.lvdash.json, com o recurso em
  resources/<nome>.dashboard.yml: warehouse_id por uma variável do bundle com lookup pelo nome do
  warehouse (crie no databricks.yml se não existir), dataset_catalog = a variável de catálogo do
  bundle e dataset_schema gold.
- Consultas com o nome da tabela sem catálogo nem schema (FROM vendas_temporais), para o mesmo
  dashboard funcionar em dev e prod.
- Tudo em português: título, subtítulo com período e fonte dos dados, nomes de gráficos e eixos.
  Canais exibidos como "E-commerce" e "Loja física". Dinheiro em R$.
- Layout de leitura rápida: título, uma linha de KPIs, gráficos, e uma tabela de detalhe para agir.
- Regras que o gráfico não pode quebrar: ticket médio é receita total ÷ número de vendas, nunca
  média de médias (SUM(receita) / SUM(total_vendas) em vendas_temporais, COUNT(*) em
  vendas_detalhadas, SUM(total_compras) em clientes_segmentacao); nunca somar clientes_unicos entre
  linhas; produto se conta por id_produto, porque há nomes repetidos; dia da semana se compara pela
  receita MÉDIA por dia, porque o período tem 5 sábados e 5 domingos e só 4 de cada dia útil.
- Data e hora estão em UTC (veja o comentário da coluna): diga isso no eixo.
- diferenca_pct_* está em pontos percentuais (10 = 10%): divida por 100 se usar o formato de %.

DASHBOARDS
1. "Diretoria Comercial": quanto vendemos, quando, em qual canal e com quais produtos.
   KPIs: receita, vendas, ticket médio e itens vendidos. Gráficos: receita por dia com uma linha por
   canal, receita por canal, receita média por dia da semana, receita por hora e receita por
   categoria. Tabela: top 10 produtos por receita. Filtros: período e canal, valendo para todos os
   widgets (prefira vendas_detalhadas como dataset principal; o top 10 precisa agregar antes do
   LIMIT, então pode ter um dataset próprio com parâmetros ligados aos mesmos filtros).
2. "Diretoria de Customer Success": quem são os melhores clientes e onde estão.
   KPIs: clientes, clientes VIP, % da receita que vem dos VIP e ticket médio. Gráficos: clientes por
   segmento, receita por segmento (VIP, TOP_TIER, REGULAR) e receita por região. Tabela: ranking de
   clientes com estado, região, segmento, compras, receita e última compra. Filtros: segmento e
   região.
3. "Diretoria de Pricing": estamos mais caros que a concorrência, e em quais produtos agir?
   Antes de desenhar, cruze classificacao_preco, categoria e possui_preco_suspeito: preço suspeito
   é erro de coleta ou promoção, e o diretor não pode reagir a ele. O dashboard precisa separar o
   que é confirmado do que precisa ser conferido.
   KPIs: produtos monitorados, mais caros que todos os concorrentes (confirmados, sem preço
   suspeito), receita desses produtos e produtos com preço suspeito a conferir. Gráficos: produtos
   por classificacao_preco separando confirmados e suspeitos, e diferença média vs. mercado por
   categoria sem os suspeitos. Tabela de ação: produtos MAIS_CARO_QUE_TODOS ordenados por receita,
   com nosso preço, preço médio e mínimo dos concorrentes, diferença em % e uma coluna "Preço a
   confirmar" (Sim/Não). Filtros: categoria e classificação.

NO FIM
Valide com --strict, faça o deploy em dev e me passe os links dos 3 dashboards publicados. Confira
os KPIs contra SQL direto na gold: receita R$ 974.077,28, 3.020 vendas e ticket R$ 322,54
(e-commerce: 2.155 vendas e R$ 705.486,21); 50 clientes, 10 VIP com 27,0% da receita, Norte como
região de maior receita (R$ 333.078,69); 215 produtos monitorados e 35 mais caros que todos, dos
quais 20 confirmados (R$ 161.375,09 de receita) e 15 com preço suspeito, todos de Tênis, que sem
nenhuma venda aparecem +100% acima do mercado. Sem os suspeitos, Beleza é a categoria mais cara
(+1,24%). Me diga o que o diretor de Pricing deve concluir disso.