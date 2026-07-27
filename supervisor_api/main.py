from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
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
    config = {"configurable": {"thread_id":payload.thread_id}}

    result = await graph.supervisor_graph.ainvoke(
        {"messages": [("user", payload.message)]},
        config=config,
    )

    reply = result["messages"][-1].content
    return {"reply": reply}