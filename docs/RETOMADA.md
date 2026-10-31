# Retomada do personal-agent-system

## Método de desenvolvimento

Continuar em etapas pequenas e explicadas: problema concreto, decisão de implementação, arquivos alterados, teste e resultado. O proprietário acompanha as escolhas e usa o projeto como aprendizado e portfólio. Não basta marcar fases concluídas no README: separar código existente de validação operacional.

## Ponto de partida observado

- Interface Telegram para texto e voz.
- FastAPI recebe mensagens e retoma conversas interrompidas.
- LangGraph separa roteamento, análise, aprovação e oferta de autoaprovação.
- A análise fica em pending_analysis antes do nó com interrupt; isso evita refazer a análise ao retomar a confirmação.
- MCP integra consulta à documentação e criação de cards no Trello.
- SQLite guarda checkpoints, decisões e regras.
- O README declara as fases 0 a 7 concluídas; nesta retomada não foram feitos testes com provedores, Telegram ou Trello para confirmar o funcionamento atual.
- A árvore Git estava limpa antes desta revisão.

## Divergência de documentação corrigida

O README informava Claude Sonnet como modelo de triagem. O código em supervisor_api/nodes/triage.py instancia ChatOpenAI com model=gpt-5.4, usando OPENAI_API_KEY. O README foi alinhado ao código. Isso não muda provedor nem custo por si só; nenhuma chamada foi realizada.

## Primeira prioridade: preservar o estado

Evidências:

- supervisor_api/graph.py abre checkpoints.db por caminho relativo.
- supervisor_api/memory/decision_log.py e rules_store.py também usam checkpoints.db.
- O serviço supervisor-api no docker-compose.yml não tem volume de dados.

Consequência: o banco fica na camada gravável do contêiner. Recriar/remover o contêiner pode perder conversas, aprovações e regras.

Próxima implementação proposta:

1. Identificar se existe um contêiner/banco em uso, sem iniciar bot ou enviar mensagens.
2. Preparar backup consistente do SQLite existente, incluindo o cuidado necessário com WAL, antes de recriar serviços.
3. Centralizar o caminho do banco por configuração.
4. Configurar armazenamento persistente no Compose e migração do banco preservado.
5. Testar gravação/leitura e retomada com dados fictícios, sem chamadas pagas ou criação de cards reais.
6. Só depois planejar a recriação acompanhada dos serviços.

Nenhum contêiner foi iniciado, reiniciado, removido ou recriado nesta revisão. O banco existente não foi alterado.

## Pontos seguintes observados no código

- Não foram encontrados arquivos de teste na listagem inicial; precisamos de uma base de testes antes de ampliar os agentes.
- A aprovação e a criação do card estão no mesmo nó retomável. Revisar comportamento de repetição/falhas e idempotência da criação antes de considerar o fluxo robusto contra reexecuções.
- A API /invoke não tem autenticação explícita em main.py; o Compose publica a porta 8000. O webhook também não valida assinatura no código observado. Revisar as fronteiras de acesso antes de exposição mais ampla.
- Os handlers do Telegram observados não restringem explicitamente os remetentes. Confirmar o uso pessoal pretendido e implementar a restrição correspondente antes de ampliar o acesso.
- Uma chamada estruturada síncrona a LLM ocorre dentro de um nó async; avaliar a execução assíncrona quando houver testes de comportamento.
- Mantemos as fases futuras (GitHub, Drive, web e produção) como roadmap até a base estar validada.

## Alterações desta etapa

- README: nome do modelo de triagem e seção de retomada.
- Este documento: estado observado, limites da inspeção e ordem sugerida de trabalho.

Não foram lidos valores do arquivo .env nem executadas chamadas a LLM, Telegram, Trello ou servidores MCP.

## Etapa local de persistência implementada

Caminho SQLite centralizado por `SUPERVISOR_DB_PATH`, bind mount no Compose,
ferramenta de backup consistente com WAL e três testes fictícios aprovados.
Inicialização das tabelas movida da importação para o startup da API.
O README e o diagnóstico anteriores foram preservados.

Acesso ao Docker negado pelo ambiente: não foi possível identificar o banco
em contêiner. Nenhum serviço foi alterado e nenhum dado real foi migrado.
Os testes não validam retomada real do LangGraph; as dependências do grafo
não estão disponíveis no runtime local utilizado.

Procedimento, limites e próxima operação: [persistência e migração](PERSISTENCIA.md).

## Configuração centralizada dos modelos (triagem via OpenRouter)

Problema: roteamento, conversa e triagem criavam `ChatOpenAI` cada um com
modelo, chave e `base_url` próprios. A triagem ia direto para a OpenAI com
`OPENAI_API_KEY`, enquanto a preferência é usar os créditos da OpenRouter.

Decisões:

- `supervisor_api/llm_config.py` concentra provedor e modelo por função
  (`router`, `chat`, `triage`), configuráveis por `LLM_<FUNCAO>_PROVIDER` e
  `LLM_<FUNCAO>_MODEL`. Padrão: tudo na OpenRouter; triagem com `openai/gpt-5.4`.
- Sem fallback: se a chave do provedor escolhido faltar, a API falha no
  startup. Uma `OPENAI_API_KEY` presente nunca cobre a falta da chave da
  OpenRouter. Trocar de provedor exige informar o modelo no formato dele.
- `base_url` sempre explícita, para que `OPENAI_BASE_URL` do ambiente não
  redirecione requisições nem a chave.
- Na OpenRouter, `provider.require_parameters=true`: a requisição só vai para
  endpoints que aceitam todos os parâmetros enviados (tools e `response_format`).
  A documentação da OpenRouter informa que esse suporte é por endpoint.
- A chamada estruturada final da triagem passou a usar `ainvoke`, sem bloquear
  o loop async. Roteamento e conversa continuam síncronos.

Arquivos: `llm_config.py` (novo), `router.py`, `nodes/general_chat.py`,
`nodes/triage.py`, `tests/test_llm_config.py` (novo), `.env.example`, README.

Validação: 5 testes novos (leitura da configuração e ausência de fallback) com
biblioteca padrão e chaves fictícias, mais `py_compile` dos módulos alterados.
A suíte completa (8 testes, incluindo os 3 de persistência) passou em Python 3.10.
Nenhuma chamada a provedor foi feita. Não foi validado: se a OpenRouter aceita
de fato tools + structured output de `openai/gpt-5.4` nessa versão do
`langchain-openai`, saldo, BYOK ou cobrança. A página do modelo foi conferida
em 31/10/2026 (existe, US$ 2,50/US$ 15 por 1M tokens), mas não lista os
parâmetros suportados. O primeiro teste real deve ser uma única ideia fictícia,
observando o painel da OpenRouter.

## Transcrição de voz via OpenRouter

Problema: `telegram_bot/bot.py` criava um `AsyncOpenAI` fixo na OpenAI direta,
com `gpt-4o-mini-transcribe` no código. Uma falha na transcrição gerava exceção
no handler e o usuário ficava sem resposta.

Contrato conferido em 31/10/2026: a OpenRouter expõe
`POST /api/v1/audio/transcriptions`, compatível com o upload multipart da OpenAI
(campos `file` e `model`), até 25 MB por upload e cerca de 60 s de
processamento. Aceita `ogg` entre os formatos, mas a documentação não confirma
o codec Opus e diz que o suporte varia por modelo/provedor. O catálogo de
transcrição lista `openai/gpt-4o-mini-transcribe`.

Decisões:

- `telegram_bot/transcription.py` com `TRANSCRIPTION_PROVIDER` e
  `TRANSCRIPTION_MODEL`; padrão OpenRouter + `openai/gpt-4o-mini-transcribe`.
  Mesma regra do supervisor: sem fallback e `base_url` explícita.
- Limite de 20 MB (o `getFile` da Bot API não entrega arquivos maiores),
  verificado antes do download quando o Telegram informa o tamanho.
- Falha de transcrição ou texto vazio geram uma resposta ao usuário, sem
  tentar outro provedor.

Validação: 5 testes simulados em `telegram_bot/tests` (configuração, ausência
de fallback, limite de tamanho e argumentos enviados, com cliente falso).
Não validado: aceitação real de OGG/Opus por esse modelo na OpenRouter, latência
e custo. O primeiro teste real deve ser um áudio curto, observando o painel.
Se OGG/Opus for recusado, a alternativa é converter para WAV antes do envio.
