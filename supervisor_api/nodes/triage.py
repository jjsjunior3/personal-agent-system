import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field
from langgraph.types import interrupt



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


# Cliente MCP que sabe como se conectar ao trello-mcp — o endereço usa
# o nome do serviço no Docker Compose, igual fizemos com o supervisor-api
# e o bot: containers se encontram pelo nome do serviço, não por IP.
mcp_client = MultiServerMCPClient(
    {
        "trello": {
            "url": "http://trello_mcp:8001/mcp",
            "transport": "streamable_http",
        }
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

Junior tem múltiplas responsabilidades simultâneas (SynerEduc, faculdade, \
estudos de IA, tutoria) e precisa de decisões objetivas, não animadoras. \
Avalie cada ideia com honestidade, considerando:

- NECESSÁRIA: resolve um problema real, hoje?
- VIÁVEL: dá pra construir com o tempo/recursos realistas dele?
- AGREGA VALOR: o retorno justifica o esforço, comparado a outras prioridades?

Seja direto e crítico. Prefira recomendar "descartar" ou "revisar_depois" \
a inflar ideias medianas."""


async def triage_node(state: dict) -> dict:
    last_message = state["messages"][-1]

    analysis = structured_triage_llm.invoke(
        [
            ("system", TRIAGE_SYSTEM_PROMPT),
            ("user", last_message.content),
        ]
    )

    resumo = (
        f"**Análise da ideia**\n\n"
        f"• Necessária: {'✅' if analysis.necessaria else '❌'}\n"
        f"• Viável: {'✅' if analysis.viavel else '❌'}\n"
        f"• Agrega valor: {'✅' if analysis.agrega_valor else '❌'}\n\n"
        f"**Recomendação:** {analysis.recomendacao}\n"
        f"{analysis.justificativa}"
    )

    if analysis.recomendacao == "seguir":
        user_response = interrupt(
            f"{resumo}\n\n🤔 Posso criar o card no Trello para essa ideia? (sim/não)"
        )

        # Verificação direta e determinística: sem custo de LLM,
        # sem latência extra. Normaliza para minúsculas e remove
        # espaços, para aceitar variações como "Sim", " sim ", "SIM".
        aprovado = user_response.strip().lower() in ("sim", "s", "yes", "y")

        if aprovado:
            tools = await mcp_client.get_tools()
            create_card_tool = next(t for t in tools if t.name == "create_card")
            card_result = await create_card_tool.ainvoke(
                {"title": last_message.content[:100], "description": resumo}
            )
            resumo += f"\n\n📌 {card_result}"
        else:
            resumo += "\n\n👍 Ok, não vou criar o card."

    return {"messages": [("assistant", resumo)]}