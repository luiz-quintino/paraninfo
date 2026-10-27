import pandas as pd
import regex as re
from datetime import datetime
from home.models import lstPagina, tbLog
from users.models import tbAssociados

            
def convert_date(date_str) -> str:
    date = ""
    if date_str:
        try:
            date = datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            pass
    return date

def save_log(request, description: str, evento_log_id: int) -> int:
    # Registra log de evento no banco de dados
    pagina_ = request.resolver_match.url_name
    pagina = lstPagina.objects.get(pagina=pagina_)
    
    if request.session.get('user_data'):
        seessao_ativa_id = request.session['user_data'].get('sessao_id', 0)
    else:
        seessao_ativa_id = 0

    log = tbLog.objects.create(
        pagina_id = pagina.id,
        evento_log_id = evento_log_id,
        sessao_ativa_id = seessao_ativa_id,
        descricao = description,
    )

    return log.id


def get_user_by_codigo_pagamento(comissao: str, codigo_pagamento: int) -> tbAssociados:
    """
        Localiza o usuário pelo código de pagamento.
    """
    user = tbAssociados.objects.filter(comissao=comissao, codigo_pagamento=codigo_pagamento).first()  # retorna o primeiro usuário encontrado ou None

    if user:
        return user
    
    return None

def get_user_by_responsible_name(comissao: str, name: str) -> tbAssociados:
    """
        Localiza o usuário pelo código de pagamento.
    """
    name = name.strip().lower()
    user = tbAssociados.objects.filter(comissao=comissao, nome_responsavel__iexact=name).first()  # retorna o primeiro usuário encontrado ou None

    if user:
        return user
    
    return None



