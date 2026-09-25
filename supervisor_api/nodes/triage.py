import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field
from langgraph.types import interrupt

from memory.decision_log import log_decision, count_consecutive_approvals, init_decision_log
from memory.rules_store import is_auto_approved, set_auto_approve, init_rules_store


class TriageAnalysis(BaseModel):
    necessaria: bool = Field(
        description="A ideia resolve um problema real e relevante hoje?"
    )
    viavel: bool = Field(
        description="É tecnicamente viável implementar com o tempo e "
        "recursos disponíveis nas próximas semanas/meses?"
    )
    agrega_valor: bool = Field(
        description="O benefício justifica o esforço de implementação?"
    )
    recomendacao: Literal["seguir", "descartar", "revisar_depois"] = Field(
        description="Decisão final consolidada com base nos três critérios acima."
    )
    justificativa: str = Field(
        description="Explicação curta (2-3 frases) do raciocínio por trás da recomendação."
    )


mcp_client = MultiServerMCPClient(
    {
        "trello": {
            "url": "http://trello_mcp:8001/mcp",
            "transport": "streamable_http",
        },
        "docs": {
            "url": "http://docs_mcp:8002/mcp",
            "transport": "streamable_http",
        },
    }
)


triage_llm = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

structured_triage_llm = triage_llm.with_structured_output(TriageAnalysis)


TRIAGE_SYSTEM_PROMPT = """Você é um analista de produto experiente, ajudando \
Junior — desenvolvedor e fundador do SynerEduc (SaaS de gestão escolar) — a \
avaliar rapidamente novas ideias de projeto ou funcionalidade.

Você tem acesso a ferramentas para consultar a documentação do SynerEduc \
(PRD, ROADMAP, decisões de arquitetura). Use list_docs() para ver quais \
documentos existem, e read_doc() para ler um documento específico — mas \
APENAS quando isso genuinamente ajudar a avaliar a ideia (ex: para checar \
se algo parecido já está planejado, ou se conflita com uma decisão já \
tomada). Para ideias simples e autoexplicativas, não é necessário consultar \
nada — responda direto.

Junior tem múltiplas responsabilidades simultâneas (SynerEduc, faculdade, \
estudos de IA, tutoria) e precisa de decisões objetivas, não animadoras. \
Avalie cada ideia com honestidade, considerando:

- NECESSÁRIA: resolve um problema real, hoje?
- VIÁVEL: dá pra construir com o tempo/recursos realistas dele?
- AGREGA VALOR: o retorno justifica o esforço, comparado a outras prioridades?

Seja direto e crítico. Prefira recomendar "descartar" ou "revisar_depois" \
a inflar ideias medianas."""


# Garante que as tabelas de memória (log de decisões e regras) existem
# antes de qualquer uso — chamado uma vez na importação do módulo,
# mesmo padrão de inicialização já usado para o grafo (build_graph).
init_decision_log()
init_rules_store()

# Identifica este tipo específico de ação para fins de memória/curadoria.
# Se no futuro outras ações de risco existirem (ex: enviar e-mail), cada
# uma teria sua própria constante e sua própria trilha de confiança.
ACTION_TYPE = "create_trello_card"


async def _investigate(user_message: str) -> list:
    """
    Etapa 1 — Investigação: roda um loop onde o Sonnet pode chamar as
    ferramentas de documentação (docs) quantas vezes achar necessário,
    até decidir que já tem contexto suficiente. Não usa a ferramenta
    do Trello aqui — essa etapa é só para reunir CONTEXTO, não para agir.

    Devolve o histórico completo da conversa (incluindo os resultados
    das ferramentas usadas), pronto para a etapa de decisão final.
    """
    all_tools = await mcp_client.get_tools()
    docs_tools = [t for t in all_tools if t.name in ("list_docs", "read_doc")]

    llm_with_tools = triage_llm.bind_tools(docs_tools)

    messages = [
        ("system", TRIAGE_SYSTEM_PROMPT),
        ("user", user_message),
    ]

    for _ in range(5):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            tool = next(t for t in docs_tools if t.name == tool_call["name"])
            tool_result = await tool.ainvoke(tool_call["args"])
            messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
            )

    return messages


async def triage_node(state: dict) -> dict:
    last_message = state["messages"][-1]

    # Etapa 1: investigação (pode ou não consultar documentação).
    investigation_messages = await _investigate(last_message.content)

    # Etapa 2: decisão final estruturada, já com todo o contexto
    # reunido na etapa anterior (incluindo qualquer documento lido).
    analysis = structured_triage_llm.invoke(investigation_messages)

    resumo = (
        f"**Análise da ideia**\n\n"
        f"• Necessária: {'✅' if analysis.necessaria else '❌'}\n"
        f"• Viável: {'✅' if analysis.viavel else '❌'}\n"
        f"• Agrega valor: {'✅' if analysis.agrega_valor else '❌'}\n\n"
        f"**Recomendação:** {analysis.recomendacao}\n"
        f"{analysis.justificativa}"
    )

    if analysis.recomendacao == "seguir":
        # Verifica se já existe confiança suficiente para pular o HITL.
        if is_auto_approved(ACTION_TYPE):
            aprovado = True
            log_decision(ACTION_TYPE, approved=True)
            resumo += "\n\n⚡ Auto-aprovado (regra ativa)."
        else:
            user_response = interrupt(
                f"{resumo}\n\n🤔 Posso criar o card no Trello para essa ideia? (sim/não)"
            )
            aprovado = user_response.strip().lower() in ("sim", "s", "yes", "y")
            log_decision(ACTION_TYPE, approved=aprovado)

            # Verifica se acabamos de completar 5 aprovações seguidas,
            # e se ainda não existe regra ativa (evita perguntar de novo
            # caso o usuário já tenha recusado ativar antes).
            if aprovado and count_consecutive_approvals(ACTION_TYPE) >= 5 and not is_auto_approved(ACTION_TYPE):
                offer_response = interrupt(
                    "💡 Notei que você aprovou a criação de card 5 vezes seguidas. "
                    "Quer que eu pare de perguntar e crie automaticamente daqui pra "
                    "frente, quando a recomendação for 'seguir'? (sim/não)"
                )
                if offer_response.strip().lower() in ("sim", "s", "yes", "y"):
                    set_auto_approve(ACTION_TYPE, True)
                    resumo += "\n\n✅ Auto-aprovação ativada para criação de cards."

        if aprovado:
            all_tools = await mcp_client.get_tools()
            create_card_tool = next(t for t in all_tools if t.name == "create_card")
            card_result = await create_card_tool.ainvoke(
                {"title": last_message.content[:100], "description": resumo}
            )
            resumo += f"\n\n📌 {card_result}"
        else:
            resumo += "\n\n👍 Ok, não vou criar o card."

    return {"messages": [("assistant", resumo)]}