# ecommerce_lakehouse

Projeto de portfólio: pipeline de analytics de e-commerce no Databricks, arquitetura
medalhão (bronze → silver → gold), dashboards AI/BI e agentes Genie por diretoria de negócio.

> Este README é um placeholder funcional. A versão completa (arquitetura, narrativa de
> negócio, prints dos dashboards) chega na fase de polimento do portfólio.

* `src/dashboards/`: dashboards AI/BI (Lakeview), um por diretoria.
* `src/ecommerce_lakehouse_etl/transformations/`: pipeline Lakeflow (silver em Python, gold em SQL).
* `resources/`: definição dos recursos do bundle (pipeline, job, dashboards).
* `testes/`: notebook de testes de qualidade, roda depois do pipeline.
* `AGENTS.md`: convenções do projeto (catálogo, nomenclatura, regras de negócio).

## Como rodar

```bash
databricks auth login --profile <seu-perfil>
databricks bundle validate --strict --profile <seu-perfil>
databricks bundle deploy -t dev --profile <seu-perfil>
databricks bundle run ecommerce_lakehouse_job -t dev --profile <seu-perfil>
```
