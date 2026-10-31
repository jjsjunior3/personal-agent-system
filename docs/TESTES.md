# Testes

## Como rodar

Da raiz do repositório:

```powershell
python scripts/run_tests.py
```

O script compila todos os arquivos Python e roda cada suíte `unittest` no
diretório do seu serviço (`supervisor_api/tests`, `telegram_bot/tests`). Usa só
a biblioteca padrão e dados/chaves fictícios: não chama Telegram, Trello, MCP
nem provedores de LLM, e não precisa do `.env`.

Se `python` abrir o atalho da Microsoft Store, use o caminho do Python 3.12
instalado ou `py -3 scripts/run_tests.py`.

## Antes de cada push

O hook `.githooks/pre-push` roda o mesmo script e bloqueia o push se algo
falhar. Ative uma vez por clone:

```powershell
git config core.hooksPath .githooks
```

Se o hook não achar o Python certo, defina `PYTHON` com o caminho do
executável. Em emergência, `git push --no-verify` pula o hook; o CI no GitHub
(`.github/workflows/tests.yml`) roda os testes de novo em cada push e pull request.

## Regra do projeto: teste junto com a mudança

Toda mudança de comportamento entra com teste no mesmo commit, sempre que for
possível testar sem chamada real:

- Configuração e regras (ex.: provedor sem chave não tem fallback): teste direto.
- Integrações externas (LLM, transcrição, Trello, Telegram): cliente falso com
  `unittest.mock`, verificando o que seria enviado.
- Bugs corrigidos: primeiro um teste que reproduz o bug, depois a correção.
- Serviço novo com `tests/`: adicionar o diretório em `SUITES` no script.

O que só pode ser validado com chamada real (custo, formato aceito pelo
provedor, cards no Trello) fica registrado como "não validado" na documentação
da etapa, com o teste manual mínimo sugerido.
