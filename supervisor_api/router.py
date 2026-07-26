import os
from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class RouteDecision(BaseModel):
    """
    Define o formato  ESTRUTURADO que o LLM deve devolver ao classificar
    uma mensage. O campo 'destino' só aceita um dos dois valores listados
    no Literal - se o modelo tentar devolver qualquer outra coisa, a
    validação do Pydantic rejeita automaticamente.
    """
    destino: Literal["geral", "triagem"] = Field(
        description=(
            "Escolha 'triagem' se a mensagem descreve uma IDEIA"
            "melhoria ou funcionalidade que precisa ser avaliada quanto"
            "a necessidade, viabilidade e valor. Escolha 'geral' para"
            "qualquer outro tipo de mensagem: conversa casual, perguntas"
            "diretas, ou pedidos que não envolvem avaliar uma nova idéia."
        )
    )

# Cliente do LLM usado exclusivamente para decisão de roteamente.
# Gemini Flash é o suficiente aqui: classificar em duas categorias é uma
# tarefa simples, não precisa de um modelo mais caro/poderoso.
router_llm = ChatOpenAI(
    model="google/gemini-2.5-flash",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# .with_structured_output(RouteDecision) reconfigura o cliente para
# SEMPRE devolver um objeto RouteDecision válido, em vez de texto livre.
structured_router_llm = router_llm.with_structured_output(RouteDecision)

def route_message(state: dict) -> Literal["geral", "triagem"]:
    """
    Função de roteamento condicional: analise a ÚLTIMA mensagem do
    usuário e decide para qual nó o grafo deve seguir.

    Diferente dos nós normais (general_chat_not, etc), essa função
    não devolve uma atualização de estado - ela devolve uma STRING,
    que o LangGraph usa para escolher o próximo nó a executar.
    """
    last_message = state["messages"][-1]

    decision = structured_router_llm.invoke(
        [
            (
                "system",
                "Você é um classificador de intenções. Analise a mensagem"
                "do usuário e decida para onde ela deve ser roteada.",
            ),
            ("user", last_message.content),
        ]
    )

    return decision.destino