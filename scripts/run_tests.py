"""Roda todas as verificações locais do projeto antes de um push.

Uso, da raiz do repositório:  python scripts/run_tests.py

1. Compila todos os .py do projeto (pega erro de sintaxe em arquivo sem teste).
2. Roda cada suíte unittest no diretório do seu serviço, em processo separado,
   porque os serviços importam módulos pelo nome local (ex.: "database").

Só usa a biblioteca padrão e não chama Telegram, Trello, MCP nem provedores
de LLM. É o mesmo comando do hook pre-push e do CI no GitHub.
"""
import compileall
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Cada serviço com pasta tests/ entra aqui. Ao criar testes num serviço
# novo, adicione o diretório dele nesta lista.
SUITES = ["supervisor_api", "telegram_bot"]

SKIP = re.compile(r"[\\/](\.git|\.venv|venv|data|backups|__pycache__)[\\/]")


def compile_sources() -> bool:
    print("== Compilando arquivos Python", flush=True)
    return compileall.compile_dir(ROOT, rx=SKIP, quiet=1, force=True)


def run_suite(service: str) -> bool:
    print(f"\n== Testes de {service}", flush=True)
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT / service,
    )
    return result.returncode == 0


def main() -> int:
    results = {"compilação": compile_sources()}
    for service in SUITES:
        results[service] = run_suite(service)

    print("\n== Resumo")
    for name, ok in results.items():
        print(f"  {'OK   ' if ok else 'FALHA'} {name}")

    if all(results.values()):
        print("Tudo certo.")
        return 0
    print("Há falhas: corrija antes do push.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
