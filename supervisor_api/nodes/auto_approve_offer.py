from langgraph.types import interrupt

from memory.rules_store import set_auto_approve

#Mesma constante do triage.py - em um projeto maio isso viria de um
#lugar, compartilhado, mas com uma única ação de risco por enquanto
#duplicar essa linha é mais simples do que criar um módulo só para ela
ACTION_TYPE = "create_trello_card"

async def auto_approve_offer_node(state: dict) -> dict:
    """
    Node separado do próposito: diferente de triage_node, este aqui
    não tem NENHUMA chamada de LLM ou tool antes do interrupt(). Isso
    significa que, se o LangGraph reexecutar essa função do zero em
    alum replay futuro, o pior caso é reler duas variáveis já lidas
    - nada caro, nada duplicado de verdade.
    """
    offer_response = interrupt(
        "💡 Notei que você aprovou a criação de card 5 vezes seguidas. "
        "Quer que eu pare de perguntar e crie automaticamente daqui pra "
        "frente, quando a recomendação for 'seguir'? (sim/não)"
    )

    aceitou = offer_response.strip().lower() in ("sim", "s", "yes", "y")

    # Gravar a decisão em dois casos, sim ou não. É isso que resolve
    # o bug de ficar perguntando denovo a cada aprovação seguinte:
    # a partir daqui existe uma linha em rules para essa ação, então
    # has_rule() passa a devolver True para sempre.
    set_auto_approve(ACTION_TYPE, aceitou)

    if aceitou:
        texto = "✅ Auto-aprovação ativada para criação de cards."
    else:
        texto = "👍 Combinado, continuo perguntando a cada vez."
    
    return {"messages": [("assistant", texto)]}