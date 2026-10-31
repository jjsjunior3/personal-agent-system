"""Configuração centralizada dos clientes LLM, por função.

Cada função (roteamento, conversa, triagem) escolhe provedor e modelo por
variável de ambiente. Não existe fallback: se a chave do provedor escolhido
faltar, o cliente não é criado e a API falha no startup com uma mensagem
clara, em vez de cobrar silenciosamente outro provedor.
"""
import os
from dataclasses import dataclass
from typing import Mapping

# Provedor -> (base_url, variável da chave). A base_url é sempre explícita:
# sem ela o ChatOpenAI aceitaria OPENAI_BASE_URL do ambiente e poderia mandar
# a requisição (e a chave) para um destino diferente do configurado aqui.
PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
}

# Função -> (provedor, modelo) padrão. Os identificadores de modelo dependem
# do provedor: na OpenRouter o GPT-5.4 é "openai/gpt-5.4"; na OpenAI, "gpt-5.4".
DEFAULTS = {
    "router": ("openrouter", "google/gemini-2.5-flash"),
    "chat": ("openrouter", "google/gemini-2.5-flash"),
    "triage": ("openrouter", "openai/gpt-5.4"),
}


@dataclass(frozen=True)
class LLMSettings:
    role: str
    provider: str
    model: str
    base_url: str
    api_key_env: str


def llm_settings(role: str, env: Mapping[str, str] = os.environ) -> LLMSettings:
    """Lê LLM_<FUNCAO>_PROVIDER e LLM_<FUNCAO>_MODEL, sem chamar nenhum provedor."""
    if role not in DEFAULTS:
        raise ValueError(f"Função de LLM desconhecida: {role}")

    prefix = f"LLM_{role.upper()}_"
    default_provider, default_model = DEFAULTS[role]
    provider = env.get(prefix + "PROVIDER", "").strip().lower() or default_provider
    if provider not in PROVIDERS:
        raise ValueError(
            f"{prefix}PROVIDER inválido: {provider!r} (use {', '.join(PROVIDERS)})"
        )

    model = env.get(prefix + "MODEL", "").strip()
    if not model:
        if provider != default_provider:
            # O modelo padrão tem o formato de outro provedor; adivinhar a
            # tradução do identificador esconderia um erro de configuração.
            raise ValueError(
                f"{prefix}MODEL é obrigatório quando {prefix}PROVIDER={provider}"
            )
        model = default_model

    base_url, api_key_env = PROVIDERS[provider]
    return LLMSettings(role, provider, model, base_url, api_key_env)


def create_chat_model(role: str, env: Mapping[str, str] = os.environ):
    """Cria o ChatOpenAI da função, exigindo a chave do provedor escolhido."""
    settings = llm_settings(role, env)
    api_key = env.get(settings.api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(
            f"{settings.api_key_env} não configurada para a função '{role}' "
            f"(provedor {settings.provider}). Não há fallback para outro provedor."
        )

    # Import tardio: a leitura da configuração acima pode ser testada sem
    # as dependências do LangChain instaladas.
    from langchain_openai import ChatOpenAI

    kwargs = {}
    if settings.provider == "openrouter":
        # Só roteia para endpoints que aceitam todos os parâmetros enviados
        # (tools, response_format). Suporte é por endpoint, não por modelo.
        kwargs["extra_body"] = {"provider": {"require_parameters": True}}

    return ChatOpenAI(
        model=settings.model,
        api_key=api_key,
        base_url=settings.base_url,
        **kwargs,
    )
