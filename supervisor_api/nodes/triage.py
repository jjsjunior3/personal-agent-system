import os
from langchain_openai import ChatOpenAI

# Versão Provisória: ainda usando o gemini flash, só para validar o
# roteamento. Na fase 2, trocamos esse cliente pelo claude Sonnet,
# ja que a análise de viabilidade se beneficia de um modelo mais forte
llm = ChatOpenAI (
    model="google/gemini-2.5-flash",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

def triage_node(state: dict) -> dict:
    """
    Nó de triagem de ideia (versão provisória). Por enquanto, apenas
    confirmar que a mensagem foi confirmada como uma idéia e ecoa isso
    de volta - a análise real de viabilidade será implantada na fase 2.
    """
    response =llm.invoke(
        [
            (
                "system",
                "Responda confirmando que você é um agente de TRIAGEM DE IDEIAS"
                "e que recebeu a mensagem do usuário. Não faça análise"
                "complete ainda - essa função ainda esta em construção",
            ),
            *state["messages"],
        ]
    )
    return {"messages":[response]}