import sqlite3
from datetime import datetime, timezone

DB_PATH = "checkpoints.db"


def init_decision_log():
    """
    Cria a tabela de decisões, se ainda não existir. Reaproveitamos o
    mesmo arquivo SQLite do checkpointer (checkpoints.db) — não faz
    sentido criar um banco separado só para isso, já que ambos vivem
    no mesmo container e servem ao mesmo propósito de persistência.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            approved INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def log_decision(action_type: str, approved: bool) -> None:
    """
    Registra uma decisão de HITL. 'action_type' identifica QUE TIPO de
    ação foi aprovada/recusada (ex: 'create_trello_card') — isso permite,
    no futuro, ter regras separadas por tipo de ação, em vez de uma
    regra única para tudo.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO decisions (action_type, approved, created_at) VALUES (?, ?, ?)",
        (action_type, int(approved), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def count_consecutive_approvals(action_type: str) -> int:
    """
    Conta quantas aprovações SEGUIDAS existem para um tipo de ação,
    olhando as decisões mais recentes primeiro e parando assim que
    encontra a primeira recusa (ou o histórico acabar).

    Exemplo: se as últimas decisões foram [sim, sim, sim, não, sim],
    o resultado é 3 — porque contamos a partir da mais recente até
    encontrar a primeira recusa.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT approved FROM decisions WHERE action_type = ? ORDER BY id DESC",
        (action_type,),
    )
    rows = cursor.fetchall()
    conn.close()

    count = 0
    for (approved,) in rows:
        if approved:
            count += 1
        else:
            break
    return count