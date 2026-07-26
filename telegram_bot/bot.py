import os
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# Carregar TELEGRAM_BOT_TOKEN do arquivo .env para o ambiente do processo.
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Endereço de API do supervisor. "supervisor-api" é o nome do serviço
# que vamos definir no docker-compose.yml - dentro da rede do Docker,
# os containers se encontram pelo nome do serviço, não por IP.
SUPERVISOR_API_URL = "http://supervisor-api:8000/invoke"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Chamada automática pela lib toda vez que o usuário manda uma
    mensagem de texto para o bot no Telegram.

    Responsabilidade única desta função: pegar a mensagem do usuário,
    repassar para a API do supervisor, e devolver a resposta.
    Nenhum lógicade agente mora aqui - o bot é só a "porta de entrada".
    """
    # ID único do usuário no Telegram. Vamos usar isso como Thread_id,
    # o que garante que o supervisor lembre o contexto deste coonversa
    # especificamente, e não misture a conversa com de outras pessoas.
    user_id = str(update.effective_user.id)
    user_message = update.message.text

    # Cliente HTTP assíncrono: "with" garante que a conexão é fechada
    # corretamente mesmo se der erro no meio da requisição
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                SUPERVISOR_API_URL,
                json={"thread_id": user_id, "message": user_message},
            )
            response.raise_for_status() # lança o erro se o status for 4xx/5xx
            reply_text = response.json()["reply"]
        except httpx.HTTPError:
            # Se a API do Supervisor estiver fora do ar ou estiver errado,
            # o usuário recebe um aviso claro em vez do bot travar em silêncio.
            reply_text = "Desculpe, não consegui falar com o agente agora, tente de novo em instantes."
    
    await update.message.reply_text(reply_text)

def main() -> None:
    """
    Ponto de entrada do bot: monta a aplicação do Telegram, registra o
    handler de mensagens, e inicia o polling (fica perguntando ao
    Telegram se chegou mensagem nova).
    """
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # filters.TEXT garante que só mensagens de texto acionam handle_message
    # (ignora, por exemplo, fotos ou stickers, que não tratamos ainda).
    # ~filters.COMMAND exclui comandos como /start, que teriam handler próprio.
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Bot iniciado. Aguardando mensagens...")
    application.run_polling()


if __name__ == "__main__":
    main()