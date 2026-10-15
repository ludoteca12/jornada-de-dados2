"""Teste de bloqueio da governança: prova que uma diretoria só lê a própria gold de prod.

Uso:
    python scripts/testar_bloqueio.py --profile <perfil>

Cria um service principal temporário, coloca no grupo de conta `diretoria_cs`, gera um
secret em memória (nunca impresso) e consulta como ele:
  - deve LER   gold.clientes_segmentacao (tabela da própria diretoria);
  - deve NEGAR gold.vendas_detalhadas (gold de outra diretoria), a silver e o catálogo de dev.
Tudo o que foi criado é apagado no fim, mesmo se algo falhar. Sai com código 1 se o
resultado não for o esperado.
"""

import argparse
import json
import os
import sys
import time

from _databricks import cli, cli_json, consultas, host_do_perfil, resumo_bundle

NEGADO = ("INSUFFICIENT_PRIVILEGES", "INSUFFICIENT_PERMISSIONS", "PERMISSION_DENIED")


def patch_op(op, path, valor):
    return json.dumps({"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                       "Operations": [{"op": op, "path": path, "value": valor}]})


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--profile", required=True)
    p.add_argument("--catalogo", default="ecommerce_lakehouse")
    p.add_argument("--catalogo-dev", default="ecommerce_lakehouse_dev")
    a = p.parse_args()

    grupos = cli_json("api", "get", "/api/2.0/account/scim/v2/Groups?filter=displayName%20eq%20%22diretoria_cs%22",
                      profile=a.profile).get("Resources", [])
    if not grupos:
        sys.exit("Grupo de conta diretoria_cs não encontrado (veja o setup no README).")
    grupo_id = grupos[0]["id"]
    warehouse = resumo_bundle("prod", a.profile)["variables"]["warehouse_id"]["value"]

    sp = cli_json("service-principals", "create", "--display-name", "sp_teste_bloqueio_temp", profile=a.profile)
    print("service principal temporário criado")
    try:
        cli("service-principals", "patch", sp["id"], "--json",
            patch_op("add", "entitlements", [{"value": "databricks-sql-access"}]), profile=a.profile)
        cli("api", "patch", f"/api/2.0/account/scim/v2/Groups/{grupo_id}", "--json",
            patch_op("add", "members", [{"value": sp["id"]}]), profile=a.profile)
        segredo = cli_json("service-principal-secrets-proxy", "create", sp["id"], profile=a.profile)["secret"]
        env = {"DATABRICKS_CONFIG_FILE": os.devnull, "DATABRICKS_HOST": host_do_perfil(a.profile),
               "DATABRICKS_CLIENT_ID": sp["applicationId"], "DATABRICKS_CLIENT_SECRET": segredo,
               "DATABRICKS_WAREHOUSE_ID": warehouse}
        time.sleep(20)  # propagação da participação no grupo

        casos = [
            ("lê a gold da própria diretoria", f"SELECT COUNT(*) FROM {a.catalogo}.gold.clientes_segmentacao", True),
            ("bloqueado na gold de outra diretoria", f"SELECT COUNT(*) FROM {a.catalogo}.gold.vendas_detalhadas", False),
            ("bloqueado na silver", f"SELECT COUNT(*) FROM {a.catalogo}.silver.vendas", False),
            ("bloqueado no catálogo de dev", f"SELECT COUNT(*) FROM {a.catalogo_dev}.gold.clientes_segmentacao", False),
        ]
        resultados = consultas([sql for _, sql, _ in casos], env=env)
        falhas = 0
        for (nome, _, deve_ler), r in zip(casos, resultados):
            leu = not isinstance(r, Exception)
            negado = not leu and any(n in str(r) for n in NEGADO)
            ok = leu if deve_ler else negado
            falhas += not ok
            detalhe = f"{r[0][0]} linhas" if leu else str(r).split(":")[0][:80]
            print(f"  {'OK  ' if ok else 'FALHA'}  {nome:<38} ({detalhe})")
    finally:
        # Com identity federation, `service-principals delete` só tira do workspace e o SP
        # continua na conta (com secret ativo). Apagar no nível da conta remove tudo.
        cli("api", "delete", f"/api/2.0/account/scim/v2/ServicePrincipals/{sp['id']}",
            profile=a.profile, check=False)
        sobrou = any(s["id"] == sp["id"] for s in cli_json("service-principals", "list", profile=a.profile))
        print("service principal temporário apagado" if not sobrou
              else f"ATENÇÃO: não foi possível apagar o service principal {sp['id']}")

    print("\nGovernança aplicada." if not falhas else f"\n{falhas} caso(s) fora do esperado.")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
