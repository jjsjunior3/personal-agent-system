from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from langgraph.types import Command
import httpx

import os

import graph

load_dotenv()

app = FastAPI(title="SupervisorAPI")

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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

async def send_telegram_notification(text: str) -> None:
    """
    Envia uma mensagem PROATIVA para o Telegram — ou seja, iniciada pelo
    sistema, não em resposta a uma mensagem do usuário. Chama a API do
    Telegram diretamente (sem passar pelo container telegram-bot), já
    que este é um fluxo de sistema, não uma conversa.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        )


@app.head("/webhooks/trello")
async def trello_webhook_verify():
    """
    O Trello faz uma requisição HEAD para esta URL antes de aceitar
    registrar o webhook — é a forma dele confirmar que a URL existe
    e responde. Não precisa fazer nada além de responder 200 OK.
    """
    return {}


@app.post("/webhooks/trello")
async def trello_webhook_receive(request: Request):
    """
    Recebe eventos reais do Trello. Filtra apenas mudanças de lista
    (card movido de uma coluna para outra) e notifica proativamente
    via Telegram quando isso acontece.
    """
    payload = await request.json()
    action = payload.get("action", {})

    if action.get("type") == "updateCard":
        list_before = action.get("data", {}).get("listBefore")
        list_after = action.get("data", {}).get("listAfter")

        if list_before and list_after:
            card_name = action.get("data", {}).get("card", {}).get("name", "card")
            text = (
                f"📋 O card \"{card_name}\" mudou de coluna:\n"
                f"{list_before['name']} → {list_after['name']}"
            )
            await send_telegram_notification(text)

    return {"status": "received"}