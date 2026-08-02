import os
from pathlib import Path
from fastmcp import FastMCP

# Caminho FIXO dentro do container, correspondente ao volume montado
# no docker-compose.yml. O agente nunca vê o caminho real do Windows —
# ele só enxerga essa pasta, isolada dentro do container.
DOCS_ROOT = Path("/app/synereduc_docs")

mcp = FastMCP("synereduc_docs")


@mcp.tool()
async def list_docs() -> str:
    """
    Lista todos os arquivos .md disponíveis na documentação do SynerEduc
    (PRD, ROADMAP, decisões de arquitetura, etc.).

    Use esta ferramenta primeiro, para saber quais documentos existem,
    antes de tentar ler o conteúdo de um arquivo específico.
    """
    files = sorted(f.name for f in DOCS_ROOT.glob("*.md"))
    return "\n".join(files) if files else "Nenhum documento .md encontrado."


@mcp.tool()
async def read_doc(filename: str) -> str:
    """
    Lê o conteúdo completo de um documento específico da pasta de
    documentação do SynerEduc, pelo nome do arquivo (ex: 'PRD.md',
    'ROADMAP.md').

    Use isso depois de list_docs(), para consultar o conteúdo de um
    documento relevante à ideia que está sendo analisada.

    Args:
        filename: Nome exato do arquivo, incluindo a extensão .md.
    """
    # Impede acesso a qualquer caminho fora da pasta autorizada —
    # por exemplo, se filename fosse "../../etc/passwd" ou similar.
    # .resolve() converte para o caminho absoluto real, e comparamos
    # se ele ainda está dentro de DOCS_ROOT.
    target = (DOCS_ROOT / filename).resolve()
    if not target.is_relative_to(DOCS_ROOT.resolve()):
        return "Erro: caminho de arquivo inválido."

    if not target.exists():
        return f"Erro: arquivo '{filename}' não encontrado."

    return target.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8002)