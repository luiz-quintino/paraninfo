import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render

from config.menus import MENU_VOLTAR
from home.models import tbLog, tbSessao
from email_app.models import tbEmail
from users.models import tbAssociados
from utils import save_log


def _email_permission(request):
    return bool(getattr(request, 'is_admin', False)) or bool(
        getattr(request, 'is_app_admin', False)
    )


@login_required
def email(request):
    if not _email_permission(request):
        messages.error(request, 'Você não tem permissão para enviar emails.')
        return redirect('user_list')

    associados = tbAssociados.objects.filter(
        comissao=request.comissao,
        situacao='ativo',
    ).exclude(email__isnull=True).exclude(email='').order_by('nome_responsavel')

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        conteudo = request.POST.get('conteudo', '').strip()
        try:
            ids = [int(value) for value in request.POST.getlist('associados')]
        except (TypeError, ValueError):
            ids = []
        recipients = list(associados.filter(id__in=set(ids)))
        if not titulo or not conteudo or not recipients:
            messages.error(request, 'Informe título, conteúdo e ao menos um associado.')
        else:
            try:
                with transaction.atomic():
                    log_id = save_log(request, 'Envio de email', 21)
                    tbEmail.objects.create(
                        titulo=titulo,
                        conteudo=conteudo,
                        distribuicao=json.dumps(ids),
                        log_id=log_id,
                    )
                    send_mail(titulo, conteudo, None, [record.email for record in recipients], fail_silently=False)
            except Exception as exc:
                messages.error(request, f'Não foi possível enviar o email: {exc}')
            else:
                messages.success(request, 'Email enviado com sucesso.')
                return redirect('email')

    context = {
        'menu_options': [MENU_VOLTAR, {'name': 'Emails enviados', 'url': '/email/email-list/', 'tip': 'Listar emails enviados'}],
        'associados': associados,
        'titulo': request.POST.get('titulo', ''),
        'conteudo': request.POST.get('conteudo', ''),
        'selected_ids': request.POST.getlist('associados'),
    }
    return render(request, 'email_app/email.html', context)


@login_required
def email_list(request):
    if not _email_permission(request):
        messages.error(request, 'Você não tem permissão para consultar emails enviados.')
        return redirect('user_list')

    registros = tbEmail.objects.all()
    context = {
        'menu_options': [MENU_VOLTAR, {'name': 'Novo email', 'url': '/email/email/', 'tip': 'Enviar um novo email'}],
        'emails': registros,
    }
    return render(request, 'email_app/email_list.html', context)


@login_required
def email_detail(request, email_id):
    if not _email_permission(request):
        return JsonResponse({'error': 'Acesso negado.'}, status=403)

    registro = tbEmail.objects.filter(id=email_id).first()
    if not registro:
        return JsonResponse({'error': 'Email não encontrado.'}, status=404)

    try:
        ids = json.loads(registro.distribuicao)
    except (TypeError, json.JSONDecodeError):
        ids = []
    nomes = list(
        tbAssociados.objects.filter(id__in=ids).order_by('nome_responsavel').values_list('nome_responsavel', flat=True)
    )
    log = tbLog.objects.filter(id=registro.log_id).first()
    remetente = 'Não identificado'
    if log:
        sessao_associado = tbSessao.objects.filter(id=log.sessao_ativa_id).select_related('usuario').first()
        if sessao_associado and sessao_associado.usuario:
            remetente = sessao_associado.usuario.nome_responsavel

    return JsonResponse({
        'data': registro.data.strftime('%d/%m/%Y %H:%M'),
        'titulo': registro.titulo,
        'conteudo': registro.conteudo,
        'distribuicao': nomes,
        'remetente': remetente,
    })
