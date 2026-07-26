from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# importar o grafo compilado criado em graph.py
from graph import supervisor_graph

# Carregar as variáveis do arquivo .env para o ambiente do processo Python.
# Precisa ser chamado antes de qualquer os.getenv() que depende delas.
load_dotenv()

# Cria a instência principal da aplicação FastAPI
# É o objeto "app" que o Uvicorn vai procurar para rodar o servidor
app = FastAPI(title="SupervisorAPI")

class InvokeRequest(BaseModel):
    """
    Define o formato esperado do corpo (body) de uma requisição para /invoke.
    """
    thread_id: str
    message: str

@app.get("/health")
async def health_check():
    """
    Endpoint simples para verificar se a API está no ar.
    """
    return {"status": "ok"}

@app.post("/invoke")
async def invoke(payload: InvokeRequest):
    """
    Endpoint que aciona o agente supervisor (LangGrph)

    O thread_id vira parte da 'config' que o LangGraph usa para saber
    QUAL conversa carrega o checkpointer - é isso que faz duas
    mensagens da mesma pessoa serem tratadas como uma conversa contínua,
    e mensagem de pessoas diferentes não se mistura.
    """
    # Monta a configuração exigida pelo LangGraph para identificar o thread.
    config = {"configurable": {"thread_id":payload.thread_id}}

    # Invoca o grafo: passamos a nova mensagem do usuário no formato
    # que o LangChain espera - uma tupla (papel, conteúdo).
    # O checkpointer, por trás dos panos, injeta o histórico já
    # existente dessa thread_id antes de chamar o nó "supervisor".
    result = supervisor_graph.invoke(
        {"messages": [("user", payload.message)]},
        config=config,
    )


    # O estado devolvido contem a lista de mensagens acumuladas;
    # a última é sempre a reposta mais recente do modelo.
    reply = result["messages"][-1].content
    return {"reply": reply}