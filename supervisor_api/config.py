"""
Configuração central do supervisor-api.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Antes, o caminho do banco SQLite estava escrito à mão em três lugares
(graph.py, memory/decision_log.py, memory/rules_store.py). Três cópias
da mesma informação significam três lugares para errar: se eu mudasse
o caminho em dois e esquecesse o terceiro, o sistema criaria DOIS bancos
distintos — o checkpointer da conversa em um arquivo e a memória de
decisões em outro. O bug não apareceria no boot; apareceria semanas
depois, com a auto-aprovação "esquecendo" aprovações que existiam.

A regra que estamos aplicando aqui é o fator III do 12-Factor App
("Config"): tudo que muda entre ambientes (minha máquina, Docker,
produção) vem de VARIÁVEL DE AMBIENTE, nunca de valor fixo no código.
O código passa a ser o mesmo em todo lugar; só o ambiente muda.
"""

import os
from pathlib import Path

# DATA_DIR é o diretório onde TODO estado persistente do supervisor vive.
#
# O valor padrão "/app/data" é o caminho DENTRO do container, e é onde o
# docker-compose.yml monta um volume nomeado. Isso é o que impede a perda
# de dados: sem volume, /app/data morre junto com o container a cada
# `docker compose up --build`; com volume, o Docker guarda esse diretório
# fora do ciclo de vida do container.
#
# O os.getenv com valor padrão permite rodar FORA do Docker também
# (ex: `DATA_DIR=./dados uvicorn main:app` na sua máquina para depurar),
# sem precisar alterar uma linha de código.
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))

# Cria o diretório se ele ainda não existir.
#
# parents=True  → cria diretórios intermediários se faltarem (ex: /app/data
#                 funciona mesmo que /app exista mas /app/data não).
# exist_ok=True → não levanta erro se o diretório JÁ existe. Sem isso, o
#                 segundo boot do container quebraria com FileExistsError,
#                 já que o volume preserva o diretório do boot anterior.
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Caminho completo do banco. Agora existe UM lugar no projeto inteiro que
# sabe onde o SQLite mora — os outros módulos importam daqui.
#
# str() porque as bibliotecas que consomem isso (sqlite3, aiosqlite)
# aceitam Path na maioria das versões, mas documentam str. Converter aqui,
# uma vez, evita depender desse detalhe em cada ponto de uso.
DB_PATH = str(DATA_DIR / "checkpoints.db")
