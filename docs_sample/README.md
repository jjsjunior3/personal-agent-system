# Documentação de exemplo

Esta pasta existe para que o `docs_mcp` tenha o que ler quando alguém clona
o repositório **sem ter a documentação real do SynerEduc**.

O conteúdo aqui é fictício e genérico, escrito apenas para demonstrar o
mecanismo de *grounding*: o agente de triagem chama `list_docs()` para
descobrir o que existe e `read_doc()` para ler o que for relevante antes de
decidir se uma ideia é necessária, viável e agrega valor.

Para apontar o sistema para a sua documentação real, defina
`SYNEREDUC_DOCS_PATH` no `.env` — veja o `.env.example`.
