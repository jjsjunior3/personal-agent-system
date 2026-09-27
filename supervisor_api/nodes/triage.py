import os
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field
from langgraph.types import interrupt

from memory.decision_log import log_decision, init_decision_log
from memory.rules_store import is_auto_approved, init_rules_store


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


# GPT-5.4, direto na OpenAI (não via OpenRouter) — usa o crédito de
# estudo da OpenAI em vez do crédito da Anthropic, reservado pro uso
# da empresa (SynerEduc). Preço: $2,50/$15 por 1M tokens, faixa
# parecida com a do Claude Sonnet que estava antes — julgar se uma
# ideia é necessária, viável e agrega valor é raciocínio de verdade,
# não classificação simples, então não compensa ir num "mini"/"nano".
triage_llm = ChatOpenAI(
    model="gpt-5.4",
    api_key=os.getenv("OPENAI_API_KEY"),
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


init_decision_log()
init_rules_store()

ACTION_TYPE = "create_trello_card"


async def _investigate(user_message: str) -> list:
    """
    Etapa 1 — Investigação: roda um loop onde o modelo pode chamar as
    ferramentas de documentação (docs) quantas vezes achar necessário,
    até decidir que já tem contexto suficiente. Não usa a ferramenta
    do Trello aqui — essa etapa é só para reunir CONTEXTO, não para agir.
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


async def triage_analyze_node(state: dict) -> dict:
    """
    Node 1 de 2 — só investiga e analisa, SEM interrupt(). Isso é
    proposital: qualquer coisa cara/não-determinística (chamadas de
    LLM) tem que ficar de fora de um node que contém interrupt(),
    porque resumir um interrupt reexecuta o node inteiro do zero. Se
    a análise estivesse no mesmo node do interrupt de aprovação, cada
    "sim" do usuário rodaria o GPT-5.4 de novo — e como o modelo não é
    determinístico, podia mudar de recomendação entre a pergunta e a
    resposta (foi exatamente esse bug que apareceu no teste).

    Guarda o resultado em pending_analysis, no ESTADO do grafo — não
    numa variável local — pra sobreviver até o próximo node rodar.
    """
    last_message = state["messages"][-1]

    investigation_messages = await _investigate(last_message.content)
    analysis = structured_triage_llm.invoke(investigation_messages)

    resumo = (
        f"**Análise da ideia**\n\n"
        f"• Necessária: {'✅' if analysis.necessaria else '❌'}\n"
        f"• Viável: {'✅' if analysis.viavel else '❌'}\n"
        f"• Agrega valor: {'✅' if analysis.agrega_valor else '❌'}\n\n"
        f"**Recomendação:** {analysis.recomendacao}\n"
        f"{analysis.justificativa}"
    )

    return {
        "pending_analysis": {
            "recomendacao": analysis.recomendacao,
            "resumo": resumo,
            "idea": last_message.content,
        }
    }


async def triage_approve_node(state: dict) -> dict:
    """
    Node 2 de 2 — só lê o resultado já pronto de pending_analysis (sem
    LLM nenhum antes do interrupt) e decide se pede aprovação. Como
    não há nada caro antes do interrupt(), resumir esse node é seguro:
    o pior caso de um replay aqui é reler duas variáveis do estado.
    """
    pending = state["pending_analysis"]
    recomendacao = pending["recomendacao"]
    resumo = pending["resumo"]
    idea = pending["idea"]

    just_approved_action = None

    if recomendacao == "seguir":
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

        if aprovado:
            all_tools = await mcp_client.get_tools()
            create_card_tool = next(t for t in all_tools if t.name == "create_card")
            card_result = await create_card_tool.ainvoke(
                {"title": idea[:100], "description": resumo}
            )
            resumo += f"\n\n📌 {card_result}"
            just_approved_action = ACTION_TYPE
        else:
            resumo += "\n\n👍 Ok, não vou criar o card."

    return {
        "messages": [("assistant", resumo)],
        "just_approved_action": just_approved_action,
    }