import sqlite3

DB_PATH = "checkpoints.db"


def init_rules_store():
    """
    Cria a tabela de regras promovidas, se ainda não existir.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rules (
            action_type TEXT PRIMARY KEY,
            auto_approve INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def is_auto_approved(action_type: str) -> bool:
    """
    Verifica se existe uma regra ativa de auto-aprovação para este
    tipo de ação. Se não houver regra nenhuma (nunca foi promovida),
    o padrão é False — ou seja, HITL continua ativo por padrão.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT auto_approve FROM rules WHERE action_type = ?",
        (action_type,),
    )
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0])


def set_auto_approve(action_type: str, enabled: bool) -> None:
    """
    Cria ou atualiza a regra de auto-aprovação para um tipo de ação.
    Usamos INSERT ... ON CONFLICT para lidar tanto com a primeira vez
    que a regra é criada quanto com atualizações futuras (ex: se você
    decidir desativar a auto-aprovação mais tarde).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO rules (action_type, auto_approve) VALUES (?, ?)
        ON CONFLICT(action_type) DO UPDATE SET auto_approve = excluded.auto_approve
        """,
        (action_type, int(enabled)),
    )
    conn.commit()
    conn.close()