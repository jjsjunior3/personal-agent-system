import os
from langchain_openai import ChatOpenAI

# Cliente do LLM para conversa geral - continua com o gemini flash via
# OpenRouter, já que é o modelo certo para esse tipo de tarefa
# (conversa contidiana, custo baixo, sem necessidade de raciocínio profundo).
llm = ChatOpenAI(
    model="google/gemini-2.5-flash",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

GENERAL_CHAT_SYSTEM_PROMPT = """Você é o assistente pessoal de Junior, parte de \
um sistema multiagente. Seu papel é conversa geral e suporte do dia a dia — \
NÃO é sua função analisar ou reavaliar ideias de produto (isso é feito por um \
agente especializado, que só é acionado quando o Junior descreve uma nova ideia \
como tal).

Se o Junior mencionar uma atualização de contexto (ex: "as escolas estão \
implantadas") que pareça relevante a uma ideia analisada antes, reconheça a \
informação brevemente, mas NÃO gere uma nova análise estruturada você mesmo — \
sugira que ele descreva a ideia de novo como "tive uma ideia: ..." para passar \
pelo processo de análise real.

Mantenha um tom direto e objetivo, sem entusiasmo exagerado ou exclamações \
desnecessárias."""

def general_chat_node(state: dict) -> dict:
    response = llm.invoke([("system", GENERAL_CHAT_SYSTEM_PROMPT)] + state["messages"])
    return {"messages": [response]}