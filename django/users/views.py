from datetime import date, datetime
from django.conf import settings
from pathlib import Path
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from email.utils import formataddr, parseaddr
import uuid as uuid_generate # Certifique-se de que o módulo uuid está importado corretamente
from django.utils.timezone import localtime, get_current_timezone, timezone, now
from datetime import timedelta, datetime
from django.urls import reverse
from users.models import tbAssociados, tbAssociadosListView, tbAssociadosCredentials, tbConvidado, lstTipoAssociado, lstSituacao
from home.models import tbLog
from paraninfo_admin.models import tbComissao
from utils import convert_date, save_log, is_admin, is_app_admin, user_role
from django.core.files.storage import FileSystemStorage
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction as db_transaction
from django.db.models import Q
from config.menus import menu_url,  MENU_USERS_INCLUIR_USUARIO, \
                                    MENU_USERS_DEFINICAO_ACESSO, \
                                    MENU_USERS_CONVIDADOS, \
                                    MENU_USERS_GERAR_CONVITE, \
                                    MENU_USERS_ACEITAR_CONVIDADOS, \
                                    MENU_VOLTAR, \
                                    MENU_PRODUTOS_USER, \
                                    MENU_PRODUTOS, \
                                    MENU_BALANCE_MY 

from config.constants import MESSAGE_TYPE_INFO, \
                             MESSAGE_TYPE_ERROR, \
                             MESSAGE_TYPE_WARNING, \
                             MESSAGE_TYPE_SUCCESS, \
                             MESSAGE_TYPE_CONFIRM

def _digits_only(value: str) -> str:
    return ''.join(character for character in value if character.isdigit())


def _email_already_in_use(email: str, exclude_uuid=None) -> bool:
    """Checa email em cadastros e contas de login, ignorando o próprio registro."""
    email = email.strip().lower()
    if not email:
        return False

    associates = tbAssociados.objects.filter(email__iexact=email, situacao='ativo')
    guests = tbConvidado.objects.filter(email__iexact=email, situacao_id=1)
    if exclude_uuid:
        associates = associates.exclude(uuid=exclude_uuid)
        guests = guests.exclude(uuid=exclude_uuid)

    auth_users = User.objects.filter(
        Q(username__iexact=email) | Q(email__iexact=email)
    )
    if exclude_uuid:
        auth_users = auth_users.exclude(last_name=str(exclude_uuid))

    return associates.exists() or guests.exists() or auth_users.exists()


def _normalize_invitation_date(value: str) -> str:
    """Aceita a data com ou sem barras e retorna dd/mm/aaaa quando válida."""
    digits = _digits_only(value)
    if len(digits) == 8:
        value = f'{digits[:2]}/{digits[2:4]}/{digits[4:]}'
    try:
        return datetime.strptime(value.strip(), '%d/%m/%Y').strftime('%d/%m/%Y')
    except ValueError:
        return ''


def _normalize_invitation_cpf(value: str) -> str:
    digits = _digits_only(value)
    if len(digits) == 11:
        return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
    return value.strip()


def _normalize_invitation_phone(value: str) -> str:
    digits = _digits_only(value)
    if len(digits) == 11:
        return f'({digits[:2]}) {digits[2:7]}-{digits[7:]}'
    if len(digits) == 10:
        return f'({digits[:2]}) {digits[2:6]}-{digits[6:]}'
    return value.strip()


def _normalize_invitation_cep(value: str) -> str:
    digits = _digits_only(value)
    if len(digits) == 8:
        return f'{digits[:5]}-{digits[5:]}'
    return value.strip()


def _invitation_date_for_form(value):
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%d/%m/%Y')
    value = str(value).strip()
    for date_format in ('%d/%m/%Y', '%Y-%m-%d', '%Y%m%d'):
        try:
            return datetime.strptime(value, date_format).strftime('%d/%m/%Y')
        except ValueError:
            continue
    return value


def _render_invitation(request, *, route_uuid, invitation_uuid=None, record=None,
                       form_uuid=None, form_data=None, message=None, expired=False):
    initial_data = {}
    if record:
        initial_data = {
            field: getattr(record, field, '') or ''
            for field in (
                'nome_responsavel', 'nascimento_responsavel', 'email', 'cpf',
                'telefone', 'aluno', 'nome_de_guerra', 'nascimento_aluno',
                'sexo', 'matricula', 'endereco', 'numero', 'complemento',
                'bairro', 'cidade', 'cep',
            )
        }
        initial_data['nascimento_responsavel'] = _invitation_date_for_form(
            initial_data['nascimento_responsavel']
        )
        initial_data['nascimento_aluno'] = _invitation_date_for_form(
            initial_data['nascimento_aluno']
        )
    if form_data:
        initial_data.update(form_data)

    if message is None:
        message = {
            'type': 'info',
            'text': 'Preencha a Ficha de Inscrição abaixo e submeta os dados para registro.',
            'title': 'Ficha de Inscrição',
            'function': '',
        }

    context = {
        'uuid': form_uuid or (str(record.uuid) if record else ''),
        'route_uuid': route_uuid,
        'invitation_uuid': invitation_uuid,
        'message': message,
        'associado': initial_data,
        'editing': record is not None,
        'expired': expired,
        'file1_name': record.foto_identidade if record else '',
        'file2_name': record.foto_endereco if record else '',
    }
    return render(request, 'users/invitation.html', context)


def invitation_view(request, uuid):
    """Cria um cadastro via convite ou permite editar o cadastro pendente pelo UUID."""
    record = tbConvidado.objects.filter(uuid=uuid).first()
    editing = record is not None
    convite_field = None

    if editing:
        if record.situacao_id != 1:
            return _render_invitation(
                request,
                route_uuid=uuid,
                record=record,
                message={
                    'type': 'error', 'title': 'Convite expirado',
                    'text': 'Este convite expirou ou não permite mais alterações.',
                },
                expired=True,
            )
        invitation_uuid = str(record.uuid)
    else:
        convite_field = tbComissao.objects.filter(convite_uuid=uuid).first()
        convite_log_field = (
            tbLog.objects.filter(id=convite_field.convite_log_id).first()
            if convite_field else None
        )
        if not convite_field or not convite_log_field:
            return _render_invitation(
                request, route_uuid=uuid,
                message={
                    'type': 'error', 'title': 'Convite inválido',
                    'text': 'Convite inválido! Solicite um novo convite.',
                },
                expired=True,
            )
        if convite_log_field.data + timedelta(days=2) < localtime(now()):
            return _render_invitation(
                request, route_uuid=uuid,
                message={
                    'type': 'error', 'title': 'Convite expirado',
                    'text': 'Convite expirado! Solicite um novo convite.',
                },
                expired=True,
            )
        invitation_uuid = uuid

    if request.method == 'GET':
        if editing:
            return _render_invitation(
                request, route_uuid=uuid, record=record,
                invitation_uuid=invitation_uuid,
            )

        form_uuid = str(uuid_generate.uuid4())
        request.session['new_uuid'] = form_uuid
        return _render_invitation(
            request, route_uuid=uuid, invitation_uuid=invitation_uuid,
            form_uuid=form_uuid,
            message={
                'type': 'info', 'title': 'Ficha de Inscrição',
                'text': f'Você recebeu um convite para participar da {convite_field.nome_comissao}.',
            },
        )

    # O link de edição é um token próprio: o UUID precisa corresponder ao registro.
    if editing:
        if str(request.POST.get('uuid', '')) != str(record.uuid) or record.situacao_id != 1:
            return _render_invitation(
                request, route_uuid=uuid, record=record,
                message={
                    'type': 'error', 'title': 'Convite expirado',
                    'text': 'Este convite expirou ou não permite mais alterações.',
                },
                expired=True,
            )
        record_uuid = str(record.uuid)
    else:
        record_uuid = request.session.get('new_uuid')
        if not record_uuid or request.POST.get('uuid') != record_uuid:
            return _render_invitation(
                request, route_uuid=uuid, invitation_uuid=invitation_uuid,
                message={
                    'type': 'error', 'title': 'Sessão expirada',
                    'text': 'Sessão expirada. Abra novamente o link do convite.',
                },
                expired=True,
            )

    cpf = _normalize_invitation_cpf(request.POST.get('cpf', ''))
    nascimento_responsavel = _normalize_invitation_date(
        request.POST.get('nascimento_responsavel', '')
    )
    nascimento_aluno = _normalize_invitation_date(
        request.POST.get('nascimento_aluno', '')
    )
    telefone = _normalize_invitation_phone(request.POST.get('telefone', ''))
    cep = _normalize_invitation_cep(request.POST.get('cep', ''))
    file_rg = request.FILES.get('file1')
    file_endereco = request.FILES.get('file2')

    form_data = {
        field: request.POST.get(field, '').strip()
        for field in (
            'nome_responsavel', 'email', 'aluno', 'nome_de_guerra', 'sexo',
            'matricula', 'endereco', 'numero', 'complemento', 'bairro', 'cidade',
        )
    }
    form_data.update({
        'cpf': cpf,
        'telefone': telefone,
        'cep': cep,
        'nascimento_responsavel': nascimento_responsavel,
        'nascimento_aluno': nascimento_aluno,
    })

    errors = []
    required_fields = (
        'nome_responsavel', 'email', 'aluno', 'nome_de_guerra', 'sexo',
        'matricula', 'endereco', 'numero', 'bairro', 'cidade',
    )
    if any(not form_data[field] for field in required_fields):
        errors.append('Preencha todos os campos obrigatórios.')
    try:
        validate_email(form_data['email'])
    except ValidationError:
        errors.append('Informe um endereço de email válido.')
    if _email_already_in_use(form_data['email'], exclude_uuid=record_uuid):
        errors.append(
            'Este email já está cadastrado e é utilizado para login. '
            'Informe outro endereço de email.'
        )
    if not nascimento_responsavel or not nascimento_aluno:
        errors.append('Informe datas válidas no formato dd/mm/aaaa.')
    if len(_digits_only(cpf)) != 11:
        errors.append('Informe um CPF com 11 números.')
    if len(_digits_only(telefone)) not in (10, 11):
        errors.append('Informe um telefone com DDD e 8 ou 9 números.')
    if len(_digits_only(cep)) != 8:
        errors.append('Informe um CEP com 8 números.')
    if tbConvidado.objects.filter(
        cpf=cpf,
        situacao_id=1,
    ).exclude(uuid=record_uuid).exists():
        errors.append('Já existe uma ficha pendente para este CPF.')
    if not editing and (not file_rg or not file_endereco):
        errors.append('Anexe o documento de identidade e o comprovante de residência.')
    for uploaded_file in (file_rg, file_endereco):
        if uploaded_file and not uploaded_file.name.lower().endswith('.jpg'):
            errors.append('Os documentos anexados devem estar no formato JPG.')

    if errors:
        return _render_invitation(
            request, route_uuid=uuid, invitation_uuid=invitation_uuid,
            record=record if editing else None,
            form_uuid=record_uuid,
            form_data=form_data,
            message={
                'type': 'error', 'title': 'Verifique os dados',
                'text': ' '.join(errors),
            },
        )

    fs = FileSystemStorage()
    if not editing:
        record = tbConvidado(uuid=record_uuid)
    record.data = convert_date(f'{datetime.now().date():%d/%m/%Y}')
    record.comissao = record.comissao if editing else convite_field.id
    record.email = form_data['email'].lower()
    record.nome_responsavel = form_data['nome_responsavel'].title()
    record.nascimento_responsavel = convert_date(nascimento_responsavel)
    record.cpf = cpf
    record.telefone = telefone
    record.aluno = form_data['aluno'].title()
    record.nome_de_guerra = form_data['nome_de_guerra'].title()
    record.sexo = form_data['sexo']
    record.nascimento_aluno = convert_date(nascimento_aluno)
    record.matricula = form_data['matricula']
    record.endereco = form_data['endereco'].title()
    record.numero = form_data['numero']
    record.complemento = form_data['complemento']
    record.bairro = form_data['bairro'].title()
    record.cidade = form_data['cidade'].title()
    record.cep = cep
    record.situacao_id = 1
    if file_rg:
        record.foto_identidade = fs.save(f'{record_uuid}_rg.jpg', file_rg)
    if file_endereco:
        record.foto_endereco = fs.save(f'{record_uuid}_endereco.jpg', file_endereco)
    record.log_id = save_log(request, 'Ficha de Cadastro', 13)
    record.save()

    edit_url = request.build_absolute_uri(
        reverse('invitation', kwargs={'uuid': record.uuid})
    )

    primeiro_nome = record.nome_responsavel.split()[0].title()

    if convite_field:
        # Novo registro
        subject = f'Ficha de Inscrição - {convite_field.nome_curto}'
        success_message = (
            f'Ilustre {primeiro_nome},\n\n'

            f'Temos o prazer de informa que a sua Ficha de Inscrição para a {convite_field.nome_curto} foi enviada com sucesso. \n'
            f'Após a análise da documentação, você receberá um email de confirmação ou alguém irá entrar em contato com você. \n\n'


            'Utilize o link abaixo caso necessite alterar alguma informação ou algum docucumento. \n'
            f'Link para edição: {edit_url}\n'
            'O link ficará disponível até que sua solicitação seja processada. \n\n\n'

            'Esse é um email automático. Não responda a esse email\n\n'

            'Atenciosamente,\n'
            f'{convite_field.nome_comissao}\n'
            f'cnpj:{convite_field.cnpj}'
        )

    else:
        # Edita um registro existente
        subject = f'Ficha de Inscrição - Revisão'
        success_message = (
                    f'Ilustre {primeiro_nome},\n\n'
        
                    f'Sua Ficha de Inscrição foi atualizada com sucesso. \n'
                    f'Após a análise da documentação, você receberá um email de confirmação ou alguém irá entrar em contato com você. \n\n'
        
        
                    'Utilize o link abaixo caso necessite alterar alguma informação ou algum docucumento. \n'
                    f'Link para edição: {edit_url}\n'
                    'O link ficará disponível até que sua solicitação seja processada. \n\n\n'
        
                    'Esse é um email automático. Não responda a esse email\n\n'

                )

    user_email = record.email
    email_error = send_uer_email(subject, success_message, user_email)

    success_message = f'Ficha de Inscrição enviada com sucesso.\nVocê receberá um email de confirmação.\nUse o link a seguir caso necesside revisar algum dado. {edit_url}'

    if email_error:
        success_message += (
            ' Não foi possível enviar o email de confirmação. '
            'Verifique o endereço cadastrado ou contate a comissão.'
        )

    return _render_invitation(
        request,
        route_uuid=record.uuid,
        invitation_uuid=str(record.uuid),
        record=record,
        message={
            'type': 'success' if not email_error else 'warning',
            'title': 'Ficha enviada',
            'text': success_message,
        },
    )


def pdf_viewer(request, uuid, document_key):
    """Serve um PDF autorizado para o convite, sem expor o caminho local."""
    invited_record = tbConvidado.objects.filter(uuid=uuid).first()
    if invited_record:
        if invited_record.situacao_id != 1:
            raise Http404('Convite expirado.')
        comissao = get_object_or_404(tbComissao, id=invited_record.comissao)
    else:
        comissao = get_object_or_404(tbComissao, convite_uuid=uuid)
        convite_log = get_object_or_404(tbLog, id=comissao.convite_log_id)
        if convite_log.data + timedelta(days=2) < localtime(now()):
            raise Http404('Convite expirado.')

    # A URL recebe uma chave lógica, nunca um caminho ou nome de arquivo livre.
    # Para disponibilizar outro documento, inclua-o nesta lista permitida.
    documents = {
        'statute': (
            Path(str(comissao.id)) / 'ESTATUTO COMISSAO DE FORMATURA.pdf',
            'Regimento Interno.pdf',
        ),
        'certificate': (
            Path('Declaracao de Praticas de Certificacao da Autoridade Certificadora.pdf'),
            'Declaracao de Praticas de Certificacao.pdf',
        ),
    }
    document = documents.get(document_key)
    if document is None:
        raise Http404('Documento não encontrado.')

    relative_path, display_name = document
    resources_root = Path(settings.RESOURCES_ROOT).resolve()
    document_path = (resources_root / relative_path).resolve()

    try:
        document_path.relative_to(resources_root)
    except ValueError:
        raise Http404('Documento não encontrado.')

    if document_path.suffix.lower() != '.pdf' or not document_path.is_file():
        raise Http404('Documento não encontrado.')

    return FileResponse(
        document_path.open('rb'),
        content_type='application/pdf',
        filename=display_name,
    )


def user_document_view(request, uuid, document_key):
    """Exibe um anexo JPG de convidado/associado após validar o acesso."""
    associated = tbAssociados.objects.filter(uuid=uuid).first()
    guest = None if associated else tbConvidado.objects.filter(uuid=uuid).first()
    record = associated or guest
    if not record:
        raise Http404('Documento não encontrado.')

    is_owner = bool(
        request.user.is_authenticated
        and associated
        and str(associated.uuid) == str(request.user.last_name)
    )
    pending_guest_link = bool(guest and guest.situacao_id == 1)
    can_review_guest = (
        request.user.is_authenticated
        and ((is_admin(request) and user_role(request) in ['presidente', 'vice-presidente', 'secretario'])
             or is_app_admin(request))
    )
    if not is_owner and not can_review_guest and not pending_guest_link:
        raise Http404('Documento não encontrado.')
    if guest and guest.situacao_id != 1 and not can_review_guest:
        raise Http404('Documento não encontrado.')
    if request.user.is_authenticated:
        if record.comissao != request.comissao and not (
            getattr(request, 'is_sys_admin', False) or getattr(request, 'is_master', False)
        ):
            raise Http404('Documento não encontrado.')

    document_field = {
        'identity': 'foto_identidade',
        'address': 'foto_endereco',
    }.get(document_key)
    if not document_field:
        raise Http404('Documento não encontrado.')

    filename = getattr(record, document_field, '')
    if not filename or Path(filename).name != filename or Path(filename).suffix.lower() != '.jpg':
        raise Http404('Documento não encontrado.')
    if not default_storage.exists(filename):
        raise Http404('Documento não encontrado.')

    return FileResponse(
        default_storage.open(filename, 'rb'),
        content_type='image/jpeg',
        filename=Path(filename).name,
        as_attachment=False,
    )
                

@login_required()
def invited_view(request):
    '''
        View para gestão de convidados novos e geração de convites
        Os convites gerados têm validade de 2 dias
    '''
    message = {'type': 'info', 'text': '', 'title': 'Convidados', 'function': ''}
    convite_link = ''
    validade = ''

    if request.method == 'POST':
        # Gera novo convite
        if request.POST.get('generate_invite', ''):
            new_uuid = str(uuid_generate.uuid4())
            log_id = save_log(request, 'Geração de Convite', 12) # 12=Geração de convite
            tbComissao.objects.filter(id=request.comissao).update(convite_uuid=new_uuid, convite_log_id=log_id)
            message['text'] = 'Convite gerado com sucesso!'
            message['type'] = MESSAGE_TYPE_SUCCESS
        
        elif request.POST.get('refused', ''):
            # Convidado foi recusado
            can_review_guest = (
                (is_admin(request) and user_role(request) in ['presidente', 'vice-presidente', 'secretario'])
                or is_app_admin(request)
            )
            if not can_review_guest:
                messages.error(request, 'Você não tem permissão para rejeitar convidados.')
                return redirect('invited')
            convidado_uuid = request.POST.get('refused', '')
            convidado_field = tbConvidado.objects.filter(
                uuid=convidado_uuid,
                comissao=request.comissao,
                situacao_id=1,
            ).first()
            if convidado_field:
                convidado_field.situacao_id = 3  # rejeitado/cancelado
                convidado_field.save(update_fields=['situacao'])
                message['text'] = f'Convidado {convidado_field.nome_responsavel} recusado com sucesso!'
                message['type'] = MESSAGE_TYPE_SUCCESS
            else:
                message['text'] = f'Convidado não encontrado, uuid:"{convidado_uuid}"'
                message['type'] = MESSAGE_TYPE_ERROR

    convite_field = tbComissao.objects.filter(id=request.comissao).first()
    if convite_field:
        convite_log_id = convite_field.convite_log_id
        convite_uuid = convite_field.convite_uuid 
        convite_log_field = tbLog.objects.filter(id=convite_log_id).first()
        if convite_log_field:
            convite_data = convite_log_field.data
            # verifica se a data de geração + 2 dias já passou
            validate_expired = convite_data + timedelta(days=2) < localtime(now())
            validade = (convite_data + timedelta(days=2)).strftime('%d/%m/%Y %H:%M')
            if not validate_expired:
                convite_link = request.build_absolute_uri(reverse('invitation', kwargs={'uuid': convite_uuid}))

    # filtra convidados com status 'novo'
    convidados = tbConvidado.objects.filter(comissao=request.comissao, situacao__situacao='novo').order_by('-id')
    if convidados:
        # gera df para exibição
        convidados_list = []
        for convidado in convidados:
            convidados_list.append({
                'nome_responsavel': convidado.nome_responsavel,
                'aluno': convidado.aluno,
                'nome_de_guerra': convidado.nome_de_guerra,
                'cpf': convidado.cpf,
                'email': convidado.email,
                'telefone': convidado.telefone,
                'data': f'{convidado.data:%d/%m/%Y}',
                'uuid': convidado.uuid,
            })
        

    # Cria side menu
    menu_options = [
        MENU_VOLTAR,
        MENU_USERS_GERAR_CONVITE,
    ]

    context = {
            'menu_options': menu_options,
            'message': message,
            'convite_link': convite_link,
            'validade': validade,
            'convidados_list': convidados_list if convidados else None,
        }
    
    return render(request, 'users/invited.html', context)

@login_required()
def user_list_view(request):
    user_records = []  # Inicializa a lista de registros
    show_search = False  # Inicializa a opção de busca como visível

    if is_admin(request):
        # Usuários com acesso admin verão todos os registros
        user_records = User.objects.all()  # Certifique-se de importar o modelo User
        show_search = True  # Oculta a opção de busca

    return render(request, 'user-list.html', {'user_records': user_records, 'show_search': show_search})

@login_required()
def user_list(request):
    user_groups = request.user.groups.values_list('name', flat=True) if request.user.is_authenticated else []
    menu_options = [MENU_VOLTAR]

    count_new_users = tbAssociados.objects.filter(situacao='novo').count

    search_query = request.GET.get('search', '')  # Obtém o texto do filtro
    associados = tbAssociadosListView.objects.only(
        'uuid',
        'codigo_associado', 
        'nome_responsavel', 
        'aluno', 
        'nome_de_guerra'
    )  # Seleciona apenas os campos necessários

    show_search = False  # Oculta a opção de busca

    if not is_admin(request):
        # Usuário com acesso "user" verá apenas o próprio registro
        associados = associados.filter(codigo_associado=request.user.username)
    else:
        # Usuários com acesso admin verão todos os registros com a mesma comissão
        associados = associados.filter(comissao=request.comissao).order_by('id') 

        if search_query:
            # Filtrar os registros com base no texto de busca
            associados = \
                associados.filter(nome_responsavel__icontains=search_query) \
                | associados.filter(aluno__icontains=search_query) \
                | associados.filter(nome_de_guerra__icontains=search_query)
        show_search = True  # Exibe a opção de busca

        # Cria side menu apenas para os perfis selecionados
        if user_role(request) in ['presidente', 'vice-presidente', 'secretario'] or is_app_admin(request):
            menu_options.append(MENU_USERS_INCLUIR_USUARIO) 
            menu_options.append(MENU_USERS_CONVIDADOS)

    # Paginação: 10 registros por página
    paginator = Paginator(associados, 10)
    page_number = request.GET.get('page')
    associados_page = paginator.get_page(page_number)

    context = {
        'associados': associados_page,
        'show_search': show_search,
        'menu_options': menu_options,
        'count_new_users': count_new_users
    }

    return render(request, 'users/user_list.html', context)  # Renderiza o template com o contexto})


@login_required()
def user_products(request, uuid):
    message = {'type': 'info', 'text': '', 'title': 'Produtos do Usuário', 'function': ''}
    user_groups = request.user.groups.values_list('name', flat=True) if request.user.is_authenticated else []
    menu_options = [MENU_VOLTAR]

    # Busca o registro pelo UUID
    associado = tbAssociados.objects.filter(uuid=uuid).first()  # Busca pelo UUID

    if not associado:
        messages.error(request, "Registro não encontrado.")
        return redirect('user_list')

    # Cria side menu
    if uuid and ('app-admin' in user_groups or 'master' in user_groups or 'sys-admin' in user_groups):
        menu_options.append(menu_url(MENU_USERS_DEFINICAO_ACESSO, url=reverse('user_credential', kwargs={'uuid': associado.uuid})))

    context = {
        'associado': associado,
        'menu_options': menu_options,
        'message': message,
    }

    return render(request, 'users/user_products.html', context)

def store_user_fields(associado, convidado, request, uuid):
    # Garantir que os campos sejam strings vazias se estiverem None
    associado_dict = {}
    associado_dict['nome_responsavel'] = associado.nome_responsavel or ''
    associado_dict['aluno'] = associado.aluno or ''
    associado_dict['nome_de_guerra'] = associado.nome_de_guerra or ''
    associado_dict['email'] = associado.email or ''
    associado_dict['nascimento_responsavel'] = _invitation_date_for_form(associado.nascimento_responsavel)
    associado_dict['cpf'] = associado.cpf or ''
    associado_dict['telefone'] = associado.telefone or ''
    associado_dict['sexo'] = associado.sexo or ''
    associado_dict['nascimento_aluno'] = _invitation_date_for_form(associado.nascimento_aluno)
    associado_dict['matricula'] = associado.matricula or ''
    associado_dict['endereco'] = associado.endereco or ''  
    associado_dict['numero'] = associado.numero or ''  
    associado_dict['complemento'] = associado.complemento or ''  
    associado_dict['bairro'] = associado.bairro or ''  
    associado_dict['cidade'] = associado.cidade or ''  
    associado_dict['cep'] = associado.cep or ''  
    associado_dict['uuid'] = uuid or ''  
    associado_dict['comissao'] = associado.comissao or request.comissao

    if convidado:
        # registros para convidado
        # extrai o id do último associado de tbAssociados
        ultimo_associado = tbAssociados.objects.filter(comissao=request.comissao).order_by('-id').first()
        if ultimo_associado and ultimo_associado.id:
            # incrementa o código de pagamento
            codigo_pagamento = str(ultimo_associado.id + 1).zfill(2)
        else:
            codigo_pagamento = '01'

        associado_dict['codigo_associado'] = f"{request.comissao:02}{associado.matricula}{codigo_pagamento}"
        associado_dict['codigo_pagamento'] = codigo_pagamento
        associado_dict['tipo'] = 'socio'  
        associado_dict['situacao'] = 'ativo'

    else:
        # registros para usuários atuais
        associado_dict['codigo_associado'] = associado.codigo_associado or ''
        associado_dict['codigo_pagamento'] = associado.codigo_pagamento or ''
        associado_dict['situacao'] = associado.situacao or ''
        associado_dict['tipo'] = associado.tipo.lower if associado.tipo else '' 

    return associado_dict
        

@login_required()
def user_record(request, uuid=None):
    message = {'type': 'info', 'text': '', 'title': 'Registro de usuário', 'function': ''}
    user_groups = request.user.groups.values_list('name', flat=True) if request.user.is_authenticated else []
    menu_options = [MENU_VOLTAR]
    convidado = False
    allow_edition = False  

    if uuid:
        # Busca o registro pelo UUID
        associado = tbAssociados.objects.filter(uuid=uuid).first()  # Busca pelo UUID
    else:
        # Cria um registro vazio para adição
        message['title'] = 'Registro de novo usuário'
        associado = tbAssociados()

    if not associado:
        # Verifica se tem convite de novo usuário para analisar
        associado = tbConvidado.objects.filter(uuid=uuid, situacao_id=1).first()
        if associado:
            convidado = True
            message['title'] = 'Registro de novo convidado'
            # link_for_user_edition = f'/user/invitation/{uuid}'
            
        else:
            # TODO: Mensagem de erro
            messages.error(request, "Registro não encontrado.")
            return redirect('user_list')

    guest_record = associado if convidado else None
    if convidado:
        # A ficha pendente não deve expor navegação para produtos/contabilidade.
        menu_options = []
        
    if (is_admin(request) and user_role(request) in ['presidente', 'vice-presidente', 'secretario']) or is_app_admin(request):
        # Usuários com acesso admin verão todos os registros
        allow_edition = True  # Oculta a opção de busca
        
    # Cria side menu
    if not convidado:
        if uuid and (user_role(request) in ['presidente', 'vice-presidente'] or is_app_admin(request)):
            menu_options.append(menu_url(MENU_USERS_DEFINICAO_ACESSO, url=reverse('user_credential', kwargs={'uuid': associado.uuid})))
            
        if uuid and (user_role(request) in ['presidente', 'vice-presidente', 'secretario'] or is_app_admin(request)):           
            menu_options.append(menu_url(MENU_PRODUTOS, url=reverse('products:product_list', kwargs={'UUID': associado.uuid})))

        if request.session['user_uuid'] == uuid or  (user_role(request) in ['presidente', 'vice-presidente', 'secretario'] or is_app_admin(request)):
            menu_options.append(menu_url(MENU_PRODUTOS_USER, url=reverse('products:product_my_list', kwargs={'UUID': associado.uuid})))
            menu_options.append(menu_url(MENU_BALANCE_MY, url=reverse('balance:balance_my', kwargs={'usuario': associado.uuid})))
    
    associado_dict = store_user_fields(associado, convidado, request, uuid)

    def render_email_error(error_text, submitted_email):
        message.update({
            'type': MESSAGE_TYPE_ERROR,
            'text': error_text,
            'title': 'Email não disponível',
        })
        associado_dict['email'] = submitted_email
        return render(request, 'users/user_record.html', {
            'associado': associado_dict,
            'allow_edition': allow_edition,
            'uuid': uuid,
            'menu_options': menu_options,
            'convidado': convidado,
            'tipo_list': lstTipoAssociado.objects.all().order_by('tipo'),
            'situacao_list': lstSituacao.objects.all().order_by('situacao'),
            'message': message,
            'identity_document_available': bool(getattr(associado, 'foto_identidade', '')),
            'address_document_available': bool(getattr(associado, 'foto_endereco', '')),
        })

    if request.method == 'POST':
        if convidado:
            can_review_guest = (
                (is_admin(request) and user_role(request) in ['presidente', 'vice-presidente', 'secretario'])
                or is_app_admin(request)
            )
            if not can_review_guest:
                messages.error(request, 'Você não tem permissão para aprovar este convidado.')
                return redirect('user_record', uuid=uuid)

            if tbAssociados.objects.filter(uuid=guest_record.uuid).exists():
                messages.error(request, 'Já existe um registro de associado para este convidado.')
                return redirect('user_record', uuid=uuid)

            ultimo_associado = tbAssociados.objects.filter(
                comissao=guest_record.comissao
            ).order_by('-id').first()
            codigo_pagamento = str((ultimo_associado.id if ultimo_associado else 0) + 1).zfill(2)

            def guest_value(field):
                value = request.POST.get(field) if field in request.POST else getattr(guest_record, field)
                return str(value or '').strip()

            guest_email = guest_value('email').lower()
            try:
                validate_email(guest_email)
            except ValidationError:
                return render_email_error(
                    'Informe um endereço de email válido antes de aprovar o convidado.',
                    guest_email,
                )
            if _email_already_in_use(guest_email, exclude_uuid=guest_record.uuid):
                return render_email_error(
                    'Este email já está cadastrado e é utilizado para login. '
                    'Altere o email da ficha antes de aprovar o convidado.',
                    guest_email,
                )

            nascimento_responsavel = convert_date(
                _invitation_date_for_form(guest_value('nascimento_responsavel'))
            )
            nascimento_aluno = convert_date(
                _invitation_date_for_form(guest_value('nascimento_aluno'))
            )

            associado = tbAssociados(
                uuid=guest_record.uuid,
                data=convert_date(localtime(now()).strftime('%d/%m/%Y')),
                email=guest_email,
                nome_responsavel=guest_value('nome_responsavel').title(),
                nascimento_responsavel=nascimento_responsavel or guest_record.nascimento_responsavel,
                cpf=guest_value('cpf'),
                telefone=guest_value('telefone'),
                aluno=guest_value('aluno').title(),
                nome_de_guerra=guest_value('nome_de_guerra').title(),
                sexo=guest_value('sexo'),
                nascimento_aluno=nascimento_aluno or guest_record.nascimento_aluno,
                matricula=guest_value('matricula'),
                endereco=guest_value('endereco').title(),
                numero=guest_value('numero'),
                complemento=guest_value('complemento'),
                bairro=guest_value('bairro').title(),
                cidade=guest_value('cidade').title(),
                cep=guest_value('cep'),
                tipo='Socio',
                situacao='novo',
                codigo_pagamento=codigo_pagamento,
                codigo_associado=f'{guest_record.comissao:02}{guest_record.matricula}{codigo_pagamento}',
                foto_identidade=guest_record.foto_identidade,
                foto_endereco=guest_record.foto_endereco,
                comissao=guest_record.comissao,
            )

            try:
                with db_transaction.atomic():
                    associado.save()
                    guest_record.situacao_id = 2
                    guest_record.save(update_fields=['situacao'])
            except IntegrityError:
                messages.error(request, 'Não foi possível aprovar o convidado. Nenhuma alteração foi concluída.')
                return redirect('user_record', uuid=uuid)

            messages.success(request, 'Convidado aprovado e associado criado com situação "novo".')
            return redirect('user_record', uuid=associado.uuid)

        submitted_email = request.POST.get('email', '').strip().lower()
        email_error = ''
        try:
            validate_email(submitted_email)
        except ValidationError:
            email_error = 'Informe um endereço de email válido.'
        if not email_error and _email_already_in_use(
            submitted_email,
            exclude_uuid=associado.uuid if uuid else None,
        ):
            email_error = (
                'Este email já está cadastrado e é utilizado para login. '
                'Informe outro endereço de email.'
            )
        if email_error:
            return render_email_error(email_error, submitted_email)

        # try:
        # Gera um UUID apenas para novos registros
        if not uuid or convidado:
            associado.data = convert_date(f'{datetime.now().date():%d/%m/%Y}')
        
            if not uuid:
                associado.uuid = str(uuid_generate.uuid4())
                associado.codigo_associado = f"{request.comissao:02}{request.POST.get('matricula')}{request.POST.get('codigo_pagamento')}"

            if convidado:
                associado.uuid = uuid

        if not request.POST.get('comissao'):    
            # se não for informada comissão, usa o da sessão
            associado.comissao = request.comissao
        else:
            # modifica a comissão do associado
            associado.comissao = request.POST.get('comissao')
        
        associado.nome_responsavel = request.POST.get('nome_responsavel')
        associado.aluno = request.POST.get('aluno')
        associado.nome_de_guerra = request.POST.get('nome_de_guerra')
        associado.codigo_pagamento = request.POST.get('codigo_pagamento')
        associado.email = request.POST.get('email')
        associado.nascimento_responsavel = convert_date(request.POST.get('nascimento_responsavel'))
        associado.cpf = request.POST.get('cpf')
        associado.telefone = request.POST.get('telefone')
        associado.sexo = request.POST.get('sexo')
        associado.nascimento_aluno = convert_date(request.POST.get('nascimento_aluno'))
        associado.matricula = request.POST.get('matricula')
        associado.endereco = request.POST.get('endereco')
        associado.numero = request.POST.get('numero')
        associado.complemento = request.POST.get('complemento')
        associado.bairro = request.POST.get('bairro')
        associado.cidade = request.POST.get('cidade')
        associado.cep = request.POST.get('cep')
        associado.tipo = request.POST.get('tipo')
        associado.situacao = request.POST.get('situacao')
        # Salva o registro
        associado.save()

        message = {'type': MESSAGE_TYPE_SUCCESS, 
                    'text': 'Registro salvo com sucesso!',
                    'title': 'Atualização de registro',
                    }


        subject = f'Associação aprovada'
        primeiro_nome = associado.nome_responsavel.split()[0].title()
        success_message = (
            f'Olá, {primeiro_nome}!\n\n'

            f'Gostaríamos de dar-lhe as boas vindas à {request.session['user_data']['comissao_title']}\n\n'

            f'Estamos preparando tudo pra você.\nAguarde algumas horas e acesso o site paraninfo.com.br. Clique em [Esqueci minha senha] e siga as instruções para gerar uma senha e acessar o sistema.\n'
            f'Acesse o sistema para ver como está o seu pagamento, as últimas notícias e tudo relacionado ao evento de formatua.\n\n'

            f'Atenciosamente,\n'
            f'{request.session['user_data']['comissao_title']},\n'

                        )

        email_error = send_uer_email(subject, success_message, associado.email)
        presidente_id = request.session['user_data']['comissao_presidente_id']
        presidente_email = tbAssociados.objects.filter(id=presidente_id).first().email
        if presidente_email:
            email_error = send_uer_email(subject, success_message, presidente_email)

        # Atualiza registros
        associado_dict = store_user_fields(associado, convidado, request, uuid)
        
    tipo_list = lstTipoAssociado.objects.all().order_by('tipo')
    situacao_list = lstSituacao.objects.all().order_by('situacao')
    context = {
        'associado': associado_dict, 
        'allow_edition': allow_edition, 
        'uuid': uuid,
        'menu_options': menu_options,
        'convidado': convidado,
        'tipo_list': tipo_list,
        'situacao_list': situacao_list,
        'message': message,
        'identity_document_available': bool(
            getattr(associado, 'foto_identidade', '')
        ),
        'address_document_available': bool(
            getattr(associado, 'foto_endereco', '')
        ),
    }

    return render(request, 'users/user_record.html', context)

@login_required
def user_credential(request, uuid):
    message = {}
    menu_options = [MENU_VOLTAR]
    # Tabela associados com apenas campos necessários
    associado = get_object_or_404(tbAssociadosCredentials, uuid=uuid)  # Busca pelo UUID
    groups = Group.objects.all().order_by('id')
    user_auth = User.objects.filter(last_name=associado.uuid).first()
    user_group_id = user_auth.groups.first().id if user_auth and user_auth.groups.exists() else 5

    allow_edition = False 

    if request.user.is_authenticated:
        logged_id = list(request.user.groups.values_list("id", flat=True))[0]

        if (is_admin(request) and logged_id <= user_group_id) or is_app_admin(request):
            # Usuários com acesso admin verão todos os registros
            allow_edition = True  # Oculta a opção de busca


    if request.method == 'POST':
        username = request.POST.get('email')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = uuid
        password = request.POST.get('password')
        group_id = request.POST.get('group') or 'socio'

        group_id = int(group_id) if group_id else 0

        if group_id < logged_id:    # Não permite definição de usuário maior que seu nível de acesso
            message = {'type': MESSAGE_TYPE_ERROR, 
                    'text': 'Você não tem permissão para essa alteração.',
                    'title': 'Definição de Acesso',
                    }
            user_group_id = user_auth.groups.first().id if user_auth and user_auth.groups.exists() else None
        else:
        
            # Criar ou atualizar o usuário
            if not user_auth:
                user_auth = User.objects.create(username=username)

            user_auth.username = email
            user_auth.email = email
            user_auth.first_name = first_name
            user_auth.last_name = last_name
            if password:
                user_auth.set_password(password)

            user_auth.save()

            log_id = save_log(request,
                            description='tbUser',
                            evento_log_id=3  # log: Definição de acesso modificada
                        )

            group = Group.objects.get(id=group_id)
            user_auth.groups.clear()
            user_auth.groups.add(group)

            # Atualiza campos
            groups = Group.objects.all()
            user_group_id = user_auth.groups.first().id if user_auth and user_auth.groups.exists() else None

            message = {'type': MESSAGE_TYPE_SUCCESS, 
                    'text': 'Credenciais atualizadas com sucesso!',
                    'title': 'Definição de Acesso',
                    }
        
    context = {
        'user': user_auth,
        'associado': associado,
        'groups': groups,
        'user_group_id': user_group_id,
        'allow_edition': allow_edition,
        'menu_options': menu_options,
        'message': message
    }
    return render(request, 'users/user_credential.html', context)

def send_uer_email(subject, message_text, user_email) -> bool:
    email_error = False
    from_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
    try:
        send_mail(
            subject=subject,
            message=(
                f'{message_text}'
            ),
            from_email=formataddr(('Paraninfo', from_address)),
            recipient_list=[user_email],
            fail_silently=False,
        )
    except Exception:
        email_error = True

    return email_error