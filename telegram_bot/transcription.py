"""Transcrição de mensagens de voz, com provedor e modelo configuráveis.

Mesma regra do supervisor (supervisor_api/llm_config.py): sem fallback.
Se a chave do provedor escolhido faltar, o bot não sobe, em vez de cobrar
silenciosamente outro provedor.
"""
import io
import os
from dataclasses import dataclass
from typing import Mapping

# Provedor -> (base_url, variável da chave). base_url explícita para que
# OPENAI_BASE_URL do ambiente não redirecione o áudio nem a chave.
PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
}

DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL = "openai/gpt-4o-mini-transcribe"

# A Bot API do Telegram só entrega arquivos de até 20 MB pelo getFile, e o
# upload multipart da OpenRouter aceita até 25 MB. O menor limite vale.
MAX_AUDIO_BYTES = 20 * 1024 * 1024


class AudioTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class TranscriptionSettings:
    provider: str
    model: str
    base_url: str
    api_key_env: str


def transcription_settings(env: Mapping[str, str] = os.environ) -> TranscriptionSettings:
    provider = env.get("TRANSCRIPTION_PROVIDER", "").strip().lower() or DEFAULT_PROVIDER
    if provider not in PROVIDERS:
        raise ValueError(
            f"TRANSCRIPTION_PROVIDER inválido: {provider!r} (use {', '.join(PROVIDERS)})"
        )

    model = env.get("TRANSCRIPTION_MODEL", "").strip()
    if not model:
        if provider != DEFAULT_PROVIDER:
            # Na OpenAI direta o identificador não tem o prefixo "openai/".
            raise ValueError(
                f"TRANSCRIPTION_MODEL é obrigatório quando TRANSCRIPTION_PROVIDER={provider}"
            )
        model = DEFAULT_MODEL

    base_url, api_key_env = PROVIDERS[provider]
    return TranscriptionSettings(provider, model, base_url, api_key_env)


def create_transcription_client(env: Mapping[str, str] = os.environ):
    """Cria o cliente compatível com /audio/transcriptions do provedor escolhido."""
    settings = transcription_settings(env)
    api_key = env.get(settings.api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(
            f"{settings.api_key_env} não configurada para a transcrição "
            f"(provedor {settings.provider}). Não há fallback para outro provedor."
        )

    # Import tardio: a configuração pode ser testada sem o SDK instalado.
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key, base_url=settings.base_url), settings


async def transcribe_voice(client, settings: TranscriptionSettings, audio_bytes: bytes) -> str:
    """Transcreve um áudio OGG/Opus do Telegram e devolve o texto."""
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioTooLargeError(f"Áudio com {len(audio_bytes)} bytes excede o limite")

    # O SDK usa o nome do arquivo para identificar o formato do áudio.
    audio_buffer = io.BytesIO(audio_bytes)
    audio_buffer.name = "voice.ogg"

    transcription = await client.audio.transcriptions.create(
        model=settings.model,
        file=audio_buffer,
        language="pt",
    )
    return transcription.text.strip()
