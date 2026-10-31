# Persistência SQLite e migração preservando dados

## Implementação

`SUPERVISOR_DB_PATH` define um caminho absoluto compartilhado por checkpoints,
decisões e regras. Sem a variável, o padrão é `supervisor_api/checkpoints.db`,
independente do diretório do terminal. Se antes a API rodava em outro diretório,
localize o banco antigo antes de iniciar: o padrão novo não o descobre sozinho.
No Compose, `/app/data/checkpoints.db` aponta para `./data/supervisor` no host.
Não execute `compose up` antes de preservar e transferir o estado antigo.

Os diretórios `data/` e `backups/` são privados e ignorados pelo Git. O contexto
da imagem também exclui bancos, arquivos WAL e SHM. Um volume preserva dados
entre recriações; não substitui cópias de segurança fora da máquina.

## Identificar o estado antigo (somente leitura)

Na raiz deste projeto, consulte:

```powershell
docker ps -a --filter label=com.docker.compose.service=supervisor-api --format '{{.ID}} {{.Names}} {{.Status}}'
docker inspect --format '{{.Config.WorkingDir}} {{json .Mounts}}' <ID>
```

Confirme que o contêiner pertence a este projeto, pois o filtro pode encontrar
APIs de outros projetos. Não imprima `docker inspect` completo nem `compose config`
completo: eles podem revelar variáveis secretas. O código antigo com `WORKDIR /app`
usa `/app/checkpoints.db`. Não confunda banco ausente com banco vazio.

## Fazer backup antes de qualquer recriação

Para um banco local, usando Python 3.12 e executando da raiz do projeto:

```powershell
python supervisor_api/backup_database.py <caminho-do-banco-existente> backups/checkpoints-antes-migracao.db
```

A ferramenta abre a origem em modo de leitura, usa `sqlite3.Connection.backup`
e verifica a integridade do resultado. Captura dados confirmados no WAL; copiar
apenas o `.db` de um processo ativo pode perder esses dados. A origem precisa
existir e o destino precisa ser novo. Não registra conteúdo de conversas.
Conexões SQLite em modo de leitura ainda podem usar os arquivos auxiliares SHM;
não é uma aquisição forense com garantia de zero escritas no sistema de arquivos.

Se o banco estiver dentro de um contêiner ativo com o código antigo, o script
pode ser executado sem instalar nada e sem iniciar a aplicação:

```powershell
Get-Content -Raw supervisor_api/backup_database.py | docker exec -i <ID> python - /app/checkpoints.db /tmp/checkpoints-preservado.db
docker cp <ID>:/tmp/checkpoints-preservado.db backups/checkpoints-preservado.db
```

Crie `backups/` antes da cópia. Confira cada código de saída e use nomes novos
para cada backup. Esses comandos escrevem apenas o backup; não os executamos
nesta etapa. Se o contêiner estiver parado, não o inicie para obter o banco:
copie `.db`, `-wal` e `-shm` existentes para uma pasta isolada e execute a
ferramenta sobre essa cópia, preservando os arquivos originais. Em um contêiner
ativo, `docker cp` separado dos arquivos brutos não garante consistência.

## Transferir e só então recriar

1. Preserve um primeiro backup verificado fora da camada do contêiner.
2. Prepare uma janela sem novas gravações, incluindo requisições em andamento.
   Faça o backup final nessa janela. Um snapshot anterior não inclui gravações
   posteriores: não promova um backup antigo enquanto a API continua recebendo trabalho.
3. Use novamente a ferramenta para copiar o backup final para o destino novo
   `data/supervisor/checkpoints.db`. Ela verifica integridade e recusa sobrescrita.
4. Confirme decisões, regras e checkpoints no banco copiado sem imprimir dados
   privados. Preserve o backup original e o contêiner antigo até verificar a restauração.
5. Só depois programe a recriação da API. Iniciar a API ou o Compose completo
   pode conectar provedores/MCP e iniciar o bot; essa operação não é parte dos
   testes locais aqui descritos.

Não restaure sobre um banco aberto nem misture o `.db` restaurado com WAL/SHM
de outra execução. Para voltar ao estado antigo, preserve primeiro qualquer
estado produzido após a migração e restaure em um destino novo, com a API parada.

## Validação local sem integrações

```powershell
Set-Location supervisor_api
python -m unittest discover -s tests -v
```

Os três testes usam apenas biblioteca padrão e dados fictícios em diretórios
temporários. Cobrem decisões, regras, snapshot com WAL aberto, reabertura,
integridade, destino existente, origem inexistente e configuração do caminho.
A tabela de checkpoint no teste é fictícia: não valida o formato do LangGraph
nem o ciclo `interrupt`/retomada. Esse teste será a próxima etapa.

## Situação observada nesta sessão

Nenhum banco foi encontrado no diretório do projeto. A consulta Docker retornou
acesso negado ao pipe; a solicitação de permissão não pôde representar esse
caminho. Portanto, existência e conteúdo de banco em contêiner permanecem
desconhecidos. Nenhum serviço foi iniciado, parado, removido ou recriado, e
nenhum banco real foi copiado ou migrado. Nenhum valor do `.env` foi lido.
