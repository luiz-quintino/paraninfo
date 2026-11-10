import pandas as pd
import regex as re
from datetime import datetime
from home.models import lstPagina, tbLog, tbSessao
from users.models import tbAssociados
from django.contrib.auth.models import User, Group
from config.constants import ATIVO
import os, traceback

def save_erro_log(request, error: dict):
    """
        Salva erro em tempo de execução RUN TIME ERROR
    """
    if error:
        for k, v in error.items():
            frames = traceback.extract_tb(v.__traceback__)
            if frames:
                erro = frames[-1]
                file_error = os.path.split(erro.filename)[-1]
                error_description = f"{k}::{v} in {file_error}.{erro.name}: {erro.lineno} {erro.line}"

                error_description = error_description[:255]
                save_log(request, error_description, 21)    # Erro de execução 


def get_user_from_log_id(log_id) -> int:
    log = tbLog.objects.filter(
        id=log_id
    ).first()

    if log:
        sessao = tbSessao.objects.filter(
            id = log.sessao_ativa_id
        ).first()

        if sessao:
            return sessao.usuario_id

    return -1

# Função para verificar se o usuário pertence ao grupo 'admin'
def is_app_admin(request) -> bool:
    uuid = request.session['user_data']['user_uuid']
    
    user = User.objects.filter(last_name=uuid).first()

    is_admin = user.groups.filter(name='sys-admin').exists() or \
            user.groups.filter(name='app-admin').exists()

    if is_admin:
        user_ = tbAssociados.objects.filter(uuid=uuid).first()
        if user_.situacao.lower() == ATIVO:
            return True
    
    return False

def is_admin(request) -> bool:
    uuid = request.session['user_data']['user_uuid']

    user = User.objects.filter(last_name=uuid).first()

    is_admin = user.groups.filter(name='sys-admin').exists() or \
            user.groups.filter(name='app-admin').exists() or \
            user.groups.filter(name='master').exists() or \
            user.groups.filter(name='staff').exists()

    if is_admin:
        user_ = tbAssociados.objects.filter(uuid=uuid).first()
        if user_.situacao.lower() == ATIVO:
            return True
    
    return False

def user_role(request) -> str:
    uuid = request.session['user_data']['user_uuid']
    # if is_admin(request):
    user_ = tbAssociados.objects.filter(uuid=uuid).first()
    return user_.tipo.lower()

def convert_date(date_str) -> str:
    date = ""
    if date_str and type(date_str) == str:
        try:
            date = datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            pass
    return date

def save_log(request, description: str, evento_log_id: int) -> int:
    """
        Salva log genérico
    """
    # Registra log de eventos
    pagina_name = request.resolver_match.url_name
    pagina = lstPagina.objects.filter(pagina=pagina_name).first() or ''
    if not pagina:
        lstPagina.objects.create(pagina=pagina_name)
        pagina = lstPagina.objects.filter(pagina=pagina_name).first()
    
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



