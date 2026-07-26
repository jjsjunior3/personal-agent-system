from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# importa o nó de conversa geral do seu novo local
from nodes.general_chat import general_chat_node

class AgentState(TypedDict):
    """
    Define o formato do "estado" que viaja entre os nós do grafo.
    continua morando aqui, porque é a definição COMPARTILHADA
    entre todos os nós - o roteador e cada agente especializado
    vão ler e escrever nesse mesmo formato de estado.
    """
    messages: Annotated[list, add_messages]

def build_graph():
    """
    Monta e compila o grafo. Retorna o objeto pronto para receber
    chamadas .invoke(), já com persistência de conversa configurada.
    """
    builder = StateGraph(AgentState)

    # Registra o nó de conversa geral, agora importado ne nodes/general_chat.py
    builder.add_node("general_chat", general_chat_node)

    # Fluxo ainda lenear por enquanto: START » general_chat » END
    # O roteamento condicional entra no próximo passo.
    builder.add_edge(START, "general_chat")
    builder.add_edge("general_chat", END)

    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(checkpointer=checkpointer)

supervisor_graph = build_graph()