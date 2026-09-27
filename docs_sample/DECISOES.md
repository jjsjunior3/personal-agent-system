# Decisões de arquitetura — exemplo

> Documento FICTÍCIO, incluído apenas para demonstrar o grounding do agente.

## Toda tabela tem Row Level Security

Decidido no início. Dado de aluno é sensível; isolar no banco é mais seguro
do que confiar que toda consulta da aplicação filtre corretamente.

## Modelos de LLM são escolhidos por complexidade da tarefa

Tarefa de classificação usa modelo barato e rápido; geração longa usa modelo
maior. O custo por conversa é registrado para permitir essa comparação.

## Ação irreversível sempre passa por aprovação humana

Nenhum agente escreve em sistema externo sem confirmação explícita. Vale para
criação de card, envio de e-mail e alteração de cadastro.
