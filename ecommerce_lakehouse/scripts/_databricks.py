"""Helpers compartilhados pelos scripts de verificação: chamam a CLI `databricks` por
subprocess, sem dependências além da própria CLI autenticada."""

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ_BUNDLE = Path(__file__).resolve().parent.parent

# Acentos no terminal do Windows.
sys.stdout.reconfigure(encoding="utf-8")


def cli(*args, profile=None, env=None, check=True):
    cmd = ["databricks", *args]
    if profile:
        cmd += ["--profile", profile]
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", cwd=RAIZ_BUNDLE,
        env={**os.environ, "MSYS_NO_PATHCONV": "1", **(env or {})},
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"falhou: {' '.join(args[:4])}\n{(r.stderr or r.stdout).strip()}")
    return r.stdout.strip() or r.stderr.strip()


def cli_json(*args, profile=None, env=None):
    return json.loads(cli(*args, "-o", "json", profile=profile, env=env))


def consultas(sqls, profile=None, env=None):
    """Roda várias consultas em paralelo e devolve, para cada uma, a lista de linhas ou o erro."""
    saida = cli("experimental", "aitools", "tools", "query", "--output", "json", *sqls,
                profile=profile, env=env, check=False)
    resultado = []
    for r in json.loads(saida):
        if r["state"] == "SUCCEEDED":
            resultado.append(r.get("rows") or [])
        else:
            resultado.append(RuntimeError((r.get("error") or {}).get("message", "erro")))
    return resultado


def host_do_perfil(profile):
    return cli_json("auth", "describe", profile=profile)["details"]["host"]


def resumo_bundle(target, profile):
    return cli_json("bundle", "summary", "-t", target, profile=profile)
