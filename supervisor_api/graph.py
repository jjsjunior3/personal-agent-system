from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

# importa o nó de conversa geral do seu novo local
from nodes.general_chat import general_chat_node
from nodes.triage import triage_node
from router import route_message

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

async def build_graph():
    builder = StateGraph(AgentState)

    # Registra os dois nós de destino possível
    builder.add_node("general_chat", general_chat_node)
    builder.add_node("triage", triage_node)

    # NOVO: em vez de uma aresta fixa (add_edge), usamos add_conditional_edeges.
    # O START chama route_message, que devolve "geral" ou "triagem"- 
    # e o dicionário abaixo mapeia cada resposta possível para o nome do nó real.
    builder.add_conditional_edges(
        START,
        route_message,
        {
            "geral": "general_chat",
            "triagem": "triage"
        },
    )

    # Os dois caminhos convergem no mesmo final
    builder.add_edge("general_chat", END)
    builder.add_edge("triage", END)


    conn = await aiosqlite.connect("checkpoints.db")
    checkpointer = AsyncSqliteSaver(conn)

    return builder.compile(checkpointer=checkpointer)

supervisor_graph = None