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

def general_chat_node(state: dict) -> dict:
    """
    Nó de conversa geral: recebe o histórico de mensagens e devolve
    uma resposta gerada pelo LLM, sem nenhuma lógica especial de
    triagem ou ferramentas. É o comportamente "padrão" do agente
    quando uma mensagem não é um ideia a ser analisada.
    """
    response = llm.invoke(state["messages"])
    return {"messages": [response]}