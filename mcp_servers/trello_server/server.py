import os
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
TRELLO_BACKLOG_LIST_ID = os.getenv("TRELLO_BACKLOG_LIST_ID")

# Instância do servidor MCP. O nome "Trello" é como ele se identifica
# para qualquer cliente (nosso agente) que se conecta a ele.
mcp = FastMCP("trello")

@mcp.tool()
async def create_card(title: str, description: str) -> str:
    """
    Cria um novo card na lista "Backlog" do board SynerEduc no Trello.

    Use essa ferramenta quando uma idéia for analisada e a recomendação
    for "seguir" - isso registra a ideia na esteira de produção real,
    para acompanhamento futuro.

    Args:
        title: Título curto e claro do card (o nome da ideia/funcionalidade).
        description: Descrição detalhada, incluindo o resumo da análise de
        viabilidade (necessário, viável, agrega valor, justificativa).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.trello.com/1/cards",
            params={
                "key": TRELLO_API_KEY,
                "token": TRELLO_TOKEN,
                "idList": TRELLO_BACKLOG_LIST_ID,
                "name": title,
                "desc": description,
            },
        )
        response.raise_for_status()
        card_data = response.json()

    return f"Card criado com sucesso: {card_data['shortUrl']}"

if __name__ == "__main__":
    # Roda o servidor MCP usando transporte HTTP, para que o
    # supervisor-api (outro container) consiga se conectar a ele
    # pela rede Docker Compose.
    mcp.run(transport="http", host="0.0.0.0", port=8001)