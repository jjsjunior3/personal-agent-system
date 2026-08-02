# Imagem Base: Python 3.12 na versão "Slim" (enxuta, sem ferramentas extras)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Define o diretório do trabalho dentro do container.
# Todos os comandos seguintes (COPY, RUN, CMD) acontecem relativos  a esse caminho.
WORKDIR /app

# Copia APENAS o requirements.txt primeiro, antes do resto do código.
# Isso é proposital: o Docker faz cache po camada (layer). Se só o código
# mudar (não as dependências), o Docker resproveita essa camada de instalação
# em vez de reinstalar tudo do zero - builds ficam muito mais rápido.
COPY requirements.txt .

# Instalar as dependências listadas no requirements.txt.
# --no-cache-dir evita guardar cache de download do pip dentro da imagem,
# o que deixaria a imagem final desnecessariamente maior.
RUN pip install --no-cache-dir -r requirements.txt

# Agora sim ciopiar o restante do codigo dentro do container
COPY . .

# Documenta (não abre de fato) que este container espera receber
# Receber conexões na porta 8000. Quem efetivamente expõe a porta é o
#docker-compose.yml, mas isso serve como documentação clara.
EXPOSE 8000

# Comando que roda quando o conteiner inicia:
# sobe o servidro Uvicorn apontando para o objeto "app" dentro do main.py,
# escutando em todas as interfaces da rede (0.0.0.0) na porta 8000.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]