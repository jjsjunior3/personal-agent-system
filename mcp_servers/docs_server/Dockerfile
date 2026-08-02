FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Documenta que esse serviço espera conexão na paorta 8001 -
# diferente da 8000 do supervisor-api, para não haver conflito
# quando os dois conteiner rodarem ao mesmo tempo.

EXPOSE 8002

CMD ["python", "server.py"]