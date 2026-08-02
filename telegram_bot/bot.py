import os
import io
import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPERVISOR_API_URL = "http://supervisor-api:8000/invoke"

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def send_to_supervisor(user_id: str, text: str) -> str:
    """
    Função compartilhada: envia um texto (seja de mansagem digitada
    ou ja transcrito de um audio) para a API do supervisor, e devolve a
    resposta. Extraída para uma função pr+opria porque agora dois
    handlers diferentes (textio e voz) precisam desse mesmo comoprtamento.
    """
    # Timeout maior que o padrão: a triagem agora pode rodar um loop de
    # investigação com várias chamadas ao Claude + tools de docs antes
    # de responder, o que pode facilmente passar de 30s.
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                SUPERVISOR_API_URL,
                json={"thread_id": user_id, "message": text},
            )
            response.raise_for_status()
            return response.json()["reply"]
        except httpx.HTTPError as e:
            print(f"DEBUG send_to_supervisor falhou: {e!r}", flush=True)
            return "Desculpe, não consegui falar com o agente agora, tente de novo em instantes."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Trata mensagens de TEXTO digitadas normalmente.
    """
    user_id = str(update.effective_user.id)
    user_message = update.message.text

    reply_text = await send_to_supervisor(user_id, user_message)
    await update.message.reply_text(reply_text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Trata mensagens de VOZ: baixa o arquivo de áudio do Telegram,
    transcreve usando Whisper, e então segue o mesmo caminho de uma
    mensagem de texto normal — o resto do sistema não sabe (e não
    precisa saber) que a mensagem original era um áudio.
    """
    user_id = str(update.effective_user.id)

    # Baixa o arquivo de voz enviado pelo usuário. O Telegram entrega
    # mensagens de voz no formato OGG/Opus.
    voice_file = await update.message.voice.get_file()
    audio_bytes = await voice_file.download_as_bytearray()

    # O SDK da OpenAI espera um objeto tipo arquivo com um nome que
    # indique a extensão (usado para identificar o formato do áudio).
    audio_buffer = io.BytesIO(audio_bytes)
    audio_buffer.name = "voice.ogg"

    transcription = await openai_client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=audio_buffer,
        language="pt",
    )

    reply_text = await send_to_supervisor(user_id, transcription.text)
    await update.message.reply_text(reply_text)

def main() -> None:
    # Timeouts padrão da lib (5s de connect/read) são curtos demais para
    # buscar/baixar arquivos de voz - qualquer latência maior com a API
    # do Telegram já derruba a chamada com TimedOut.
    request = HTTPXRequest(connect_timeout=15.0, read_timeout=30.0)
    application = (
        Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).build()
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    # NOVO: registra um handler específico para mensagens de voz.
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("Bot iniciado. Aguardando mensagens...")
    application.run_polling()


if __name__ == "__main__":
    main()