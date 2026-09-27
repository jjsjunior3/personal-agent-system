from typing import Annotated, Literal, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

from nodes.general_chat import general_chat_node
from nodes.triage import triage_analyze_node, triage_approve_node
from nodes.auto_approve_offer import auto_approve_offer_node
from router import route_message
from memory.decision_log import count_consecutive_approvals
from memory.rules_store import has_rule

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    # Ponte entre triage_analyze_node e triage_approve_node: a análise
    # já pronta, calculada uma única vez, pra o node de aprovação nunca
    # precisar chamar o LLM de novo (nem em replay de interrupt).
    pending_analysis: dict | None
    # Preenchido por triage_approve_node só quando um card acabou de
    # ser criado nesta execução. Usado por route_after_triage pra
    # decidir se oferece a auto-aprovação.
    just_approved_action: str | None


def route_after_triage(state: AgentState) -> str:
    action_type = state.get("just_approved_action")
    if not action_type:
        return END
    if has_rule(action_type):
        return END
    if count_consecutive_approvals(action_type) < 5:
        return END
    return "offer_auto_approve"


async def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("general_chat", general_chat_node)
    builder.add_node("triage_analyze", triage_analyze_node)
    builder.add_node("triage_approve", triage_approve_node)
    builder.add_node("offer_auto_approve", auto_approve_offer_node)

    builder.add_conditional_edges(
        START,
        route_message,
        {
            "geral": "general_chat",
            "triagem": "triage_analyze",
        },
    )

    builder.add_edge("general_chat", END)
    builder.add_edge("triage_analyze", "triage_approve")
    builder.add_conditional_edges(
        "triage_approve",
        route_after_triage,
        {"offer_auto_approve": "offer_auto_approve", END: END},
    )
    builder.add_edge("offer_auto_approve", END)

    conn = await aiosqlite.connect("checkpoints.db")
    checkpointer = AsyncSqliteSaver(conn)

    return builder.compile(checkpointer=checkpointer)

supervisor_graph = None