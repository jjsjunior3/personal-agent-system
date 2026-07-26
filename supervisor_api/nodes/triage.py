import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

class TriageAnalysis(BaseModel):
    """
    Formato estruturado de análise de uma ideia. Usar um schema aqui
    (em vez de texto livre) é o que vai permitir, nas próximas fases,
    decidir programaticamente se um card deve ser criado no Trello
    (por exemplo, só quando recomendação == "seguir").
    """
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
        description="Decisão consolidada com base nos três critérios acima."
    )
    justificativa: str = Field(
        description="Explicação curta (2-3 frases) do raciocínio por trás da recomendação."
    )

# Cliente do Claude Sonnet, usado especificamente para análise de
# viabilidade - uma tarefa que se beneficia de raciocínio mais forte,
# diferente da classificação simples feita pelo router
triage_llm = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

structured_triage_llm = triage_llm.with_structured_output(TriageAnalysis)

TRIAGE_SYSTEM_PROMPT = """ Você é um analista de produto experiente, ajudando\
Junior - desenvolvedor e fundador do SynerEduc (Saas de gestão Escolar) - a\
avaliar rapidamente novas ideias com honestidade, considerando:
- NECESSÁRIO: resolve um problema real, hoje?
- VIÁVEL: dá para construir com o tempo/recursos realista dele?
- AGREGA VALOR: O retorno justifica o esforço, comparando a outras prioridades?

seja direto e crítico, Prefira recomendar "descartar" ou "revisar_depois"\
a inflar ideias medianas."""

def triage_node(state: dict) -> dict:
    """
    Nó de triagem de ideias: recebe a última mensagem do usuário,
    roda a análise estruturada com Claude Sonnet, e devolve uma
    resposta em texte legível - mantendo o formato estruturado
    disponível internamente para uso nas próximas fases (Trello).
    """
    last_message = state["messages"][-1]

    analysis = structured_triage_llm.invoke(
        [
            ("system", TRIAGE_SYSTEM_PROMPT),
            ("user", last_message.content),
        ]
    )

    # Montar uma resposta legível em texto a partir do objetivo estruturado
    # Isso é o que o usuário ver no telegram: o objetivo 'analysis' em si
    # (com os campos booleanos) será programaticamente a fase 3.

    resumo = (
        f"**Análise da ideia**\n\n"
        f"• Necessária: {'✅' if analysis.necessaria else '❌'}\n"
        f"• Viável: {'✅' if analysis.viavel else '❌'}\n"
        f"• Agrega valor: {'✅' if analysis.agrega_valor else '❌'}\n\n"
        f"**Recomendação:** {analysis.recomendacao}\n"
        f"{analysis.justificativa}"
    )

    return {"messages": [("assistant", resumo)]}