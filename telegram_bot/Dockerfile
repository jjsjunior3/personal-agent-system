FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Não ah o EXPOSE aqui.
# Bot não recebe conexões de fora - ele é o cliente que inicia
# conexões (para o telegram e para a API do supervisor), não um supervisor
# que escuta uma porta. Não vai sentido expor uma porta que nada usa.
CMD ["python", "bot.py"]