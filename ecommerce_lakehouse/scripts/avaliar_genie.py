"""Roda os benchmarks dos Genie Spaces de prod e mostra o placar.

Uso:
    python scripts/avaliar_genie.py --profile <perfil>

Cada espaço tem benchmarks com a resposta esperada em src/genie/*.json. O Genie gera o SQL de
novo a cada pergunta e a avaliação compara o resultado com o esperado. Sai com código 1 se
alguma pergunta não for julgada correta.
"""

import argparse
import sys
import time

from _databricks import cli_json, resumo_bundle


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--profile", required=True)
    p.add_argument("--target", default="prod")
    a = p.parse_args()

    espacos = resumo_bundle(a.target, a.profile)["resources"].get("genie_spaces", {})
    if not espacos:
        sys.exit(f"Nenhum Genie Space no target {a.target}.")

    runs = {}
    for nome, r in espacos.items():
        run = cli_json("genie", "genie-create-eval-run", r["id"], profile=a.profile)
        runs[nome] = (r["id"], run["eval_run_id"])
        print(f"avaliação iniciada: {nome}")

    total_ok = total = 0
    for nome, (space, run) in runs.items():
        for _ in range(60):
            st = cli_json("genie", "genie-get-eval-run", space, run, profile=a.profile)
            if st.get("eval_run_status") == "DONE":
                break
            time.sleep(10)
        ok, n = st.get("num_correct", 0), st.get("num_questions", 0)
        total_ok, total = total_ok + ok, total + n
        print(f"\n{nome}: {ok}/{n}")
        if ok < n:
            for res in cli_json("genie", "genie-list-eval-results", space, run, profile=a.profile).get("eval_results", []):
                det = cli_json("genie", "genie-get-eval-result-details", space, run, res["result_id"], profile=a.profile)
                if det.get("assessment") != "GOOD":
                    gerado = " ".join(x.get("response", "") for x in det.get("actual_response", []))
                    print(f"  ✗ {res['question']}\n    motivo: {det.get('assessment_reasons')}\n    SQL gerado: {gerado[:300]}")

    print(f"\nTotal: {total_ok}/{total} benchmarks corretos.")
    sys.exit(0 if total and total_ok == total else 1)


if __name__ == "__main__":
    main()
