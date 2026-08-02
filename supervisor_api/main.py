from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from langgraph.types import Command

import os

import graph

load_dotenv()

app = FastAPI(title="SupervisorAPI")

@app.on_event("startup")
async def startup_event():
    """
    Roda uma única vez, quando o servidor FASTAPI inicia. É aqui que
    finalmente construimos o grafo de verdade, já que o build_graph()
    precisa de 'await' e não pode rodar no nível do módulo.
    """
    graph.supervisor_graph = await graph.build_graph()

class InvokeRequest(BaseModel):
    thread_id: str
    message: str


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/invoke")
async def invoke(payload: InvokeRequest):
    config = {"configurable": {"thread_id": payload.thread_id}}

    current_state = await graph.supervisor_graph.aget_state(config)

    if current_state.next:
        result = await graph.supervisor_graph.ainvoke(
            Command(resume=payload.message),
            config=config,
        )
    else:
        result = await graph.supervisor_graph.ainvoke(
            {"messages": [("user", payload.message)]},
            config=config,
        )

    # Verifica se o grafo pausou (interrupt) nesta execução. O dict
    # devolvido por ainvoke() não expõe de forma confiável a chave
    # "__interrupt__" quando o nó é alcançado via aresta condicional a
    # partir do START (é o nosso caso, com route_message) — por isso
    # confirmamos a pausa consultando o estado persistido, que reflete
    # corretamente a interrupção em post_state.tasks[*].interrupts.
    post_state = await graph.supervisor_graph.aget_state(config)

    if post_state.next and post_state.tasks and post_state.tasks[0].interrupts:
        reply = post_state.tasks[0].interrupts[0].value
    else:
        reply = result["messages"][-1].content

    return {"reply": reply}