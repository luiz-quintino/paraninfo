from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import LoginView
import uuid as uuid_generate # Certifique-se de que o módulo uuid está importado corretamente
from django.utils.timezone import localtime, get_current_timezone, timezone, now
from datetime import timedelta, datetime
from django.urls import reverse
from users.models import tbAssociados, tbAssociadosListView, tbAssociadosCredentials, tbConvidado, lstTipoAssociado, lstSituacao
from home.models import tbLog
from paraninfo_admin.models import tbComissao
from utils import convert_date, save_log
from django.core.files.storage import FileSystemStorage
from config.menus import menu_url,  MENU_USERS_INCLUIR_USUARIO, \
                                    MENU_USERS_DEFINICAO_ACESSO, \
                                    MENU_USERS_CONVIDADOS, \
                                    MENU_USERS_GERAR_CONVITE, \
                                    MENU_USERS_ACEITAR_CONVIDADOS, \
                                    MENU_VOLTAR

from config.constants import MESSAGE_TYPE_INFO, \
                                MESSAGE_TYPE_ERROR, \
                                    MESSAGE_TYPE_WARNING, \
                                        MESSAGE_TYPE_SUCCESS, \
                                            MESSAGE_TYPE_CONFIRM



# Função para verificar se o usuário pertence ao grupo 'admin'
def is_sys_admin(user):
    is_admin = user.groups.filter(name='sys-admin').exists() or \
                user.groups.filter(name='app-admin').exists() or \
                user.groups.filter(name='master').exists()
    return is_admin

def invitation_view(request, uuid):
    '''
        View para aceitar convite e preencher ficha de cadastro
    '''
    message = {'type': 'info', 'text': '', 'title': 'Ficha de Inscrição', 'function': ''}
    
    # Verifica se o convite existe e é válido
    convite_field = tbComissao.objects.filter(convite_uuid=uuid).first()
    
    if not convite_field:
        # Convite não encontrado
        messages.error(request, "Convite inválido! Solicite um novo convite.")
        return redirect('login')
    
    else:
        # Convite encontrado
        convite_log_id = convite_field.convite_log_id
        convite_log_field = tbLog.objects.filter(id=convite_log_id).first()
        
        if convite_log_field:
            # verifica a validade do convite
            convite_data = convite_log_field.data
            validate_expired = convite_data + timedelta(days=2) < localtime(now())
            
            if validate_expired:
                # convite expirado
                messages.error(request, "Convite expirado! Solicite um novo convite.")
                return redirect('login')
        else:
            # convite inválido
            messages.error(request, "Convite inválido! Solicite um novo convite.")
            return redirect('login')

    # Registra solicitação do convidado
    if request.method == 'POST':
        # recupera uuid da sessão
        new_uuid = request.session.get('new_uuid')
        session_uuid = request.POST.get('uuid')

        if not new_uuid or session_uuid != new_uuid:
            # sessão inválida ou expirada
            messages.error(request, "Sessão expirada!")
            return redirect('login')
        
        # verifica se o cpf do convidado já existe em tbConvidados com status 'Ativo'
        existing_convidado = tbConvidado.objects.filter(cpf=request.POST.get('cpf'), situacao__situacao='novo').first()
        if not existing_convidado:
            messages.error(request, "Usuário já cadastrado! Entre em contato com a comissão.")
            return redirect('login')

        file_rg = request.FILES.get('file1')
        file_endereco = request.FILES.get('file2')
        nome_de_guerra = request.POST.get('nome_de_guerra').strip().title()

        fs = FileSystemStorage()
        if file_rg:
            filename1 = fs.save(f'{new_uuid}_rg.jpg', file_rg)   # salva o arquivo
        else:
            filename1 = ''      # sem arquivo

        if file_endereco:
            filename2 = fs.save(f'{new_uuid}_endereco.jpg', file_endereco)
        else:
            filename2 = ''
        
        log_id = save_log(request, 'Ficha de Cadastro', 13) # 13=Registro de convite

        # salva os dados do formulário
        tbConvidado.objects.create(
            data=convert_date(f'{datetime.now().date():%d/%m/%Y}'),
            uuid = new_uuid,
            comissao=convite_field.id,
            email=request.POST.get('email').strip().lower(),
            nome_responsavel=request.POST.get('nome_responsavel').strip().title(),
            nascimento_responsavel=convert_date(request.POST.get('nascimento_responsavel')),
            cpf=request.POST.get('cpf'),
            telefone=request.POST.get('telefone'),
            aluno=request.POST.get('aluno').strip().title(),
            nome_de_guerra=nome_de_guerra,
            sexo=request.POST.get('sexo'),
            nascimento_aluno=convert_date(request.POST.get('nascimento_aluno')),
            matricula=request.POST.get('matricula'),
            endereco=request.POST.get('endereco').title(),
            numero=request.POST.get('numero'),
            complemento=request.POST.get('complemento'),
            bairro=request.POST.get('bairro').strip().title(),
            cidade=request.POST.get('cidade').strip().title(),
            cep=request.POST.get('cep'),
            foto_identidade=filename1,
            foto_endereco=filename2,
            situacao_id=1,  # Define o status como 'novo'
            log_id = log_id
        )

        messages.success(request, 'Ficha de Inscrição enviada com sucesso!')
        return redirect('login')
    
    else:
        # convite válido, gera uuid de sessão
        new_uuid = str(uuid_generate.uuid4())

        # armazena o novo uuid na sessão
        request.session['new_uuid'] = new_uuid

        message['text'] = f"Você recebeu um convite para particiar da {convite_field.nome_comissao}"
        context = {
            'uuid': new_uuid,
            'message': message}

        return render(request, 'users/invitation.html', context)
                

@user_passes_test(is_sys_admin)
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
            convidado_uuid = request.POST.get('refused', '')
            convidado_field = tbConvidado.objects.filter(uuid=convidado_uuid, comissao=request.comissao).first()
            if convidado_field:
                convidado_field.situacao_id = 3 # cancelado
                convidado_field.save()
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

    if request.user.is_authenticated:
        is_admin = request.user.groups.filter(name="app-admin").exists() \
                  or request.user.groups.filter(name="master").exists() \
                  or request.user.groups.filter(name="sys-admin").exists() 
            
        if is_admin:
            # Usuários com acesso admin verão todos os registros
            user_records = User.objects.all()  # Certifique-se de importar o modelo User
            show_search = True  # Oculta a opção de busca

    return render(request, 'user-list.html', {'user_records': user_records, 'show_search': show_search})

@login_required()
def user_list(request):
    user_groups = request.user.groups.values_list('name', flat=True) if request.user.is_authenticated else []
    menu_options = [MENU_VOLTAR]

    search_query = request.GET.get('search', '')  # Obtém o texto do filtro
    associados = tbAssociadosListView.objects.only(
        'codigo_associado', 
        'nome_responsavel', 
        'aluno', 
        'nome_de_guerra'
    )  # Seleciona apenas os campos necessários

    show_search = False  # Oculta a opção de busca

    if request.user.is_authenticated:
        is_admin = request.user.groups.filter(name="app-admin").exists() \
                  | request.user.groups.filter(name="master").exists() \
                  | request.user.groups.filter(name="sys-admin").exists()

        if not is_admin:
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

        # Cria side menu
        if 'app-admin' in user_groups or 'master' in user_groups or 'sys-admin' in user_groups:
            menu_options.append(MENU_USERS_INCLUIR_USUARIO) 
            menu_options.append(MENU_USERS_CONVIDADOS)

    else:
        associados = tbAssociadosListView.objects.none()  # Retorna uma lista vazia para usuários não autenticados

    # Paginação: 10 registros por página
    paginator = Paginator(associados, 10)
    page_number = request.GET.get('page')
    associados_page = paginator.get_page(page_number)

    context = {
        'associados': associados_page,
        'show_search': show_search,
        'menu_options': menu_options,
    }

    return render(request, 'users/user_list.html', context)  # Renderiza o template com o contexto})

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
        associado = tbConvidado.objects.filter(uuid=uuid, situacao__situacao='novo').first()
        if associado:
            convidado = True
            message['title'] = 'Registro de novo convidado'
            
        else:
            # TODO: Mensagem de erro
            messages.error(request, "Registro não encontrado.")
            return redirect('user_list')
    print('convidado', convidado, associado)
    if request.user.is_authenticated:
        is_admin = request.user.groups.filter(name="app-admin").exists() \
                  or request.user.groups.filter(name="master").exists() \
                  or request.user.groups.filter(name="sys-admin").exists() 
        
        if is_admin:
            # Usuários com acesso admin verão todos os registros
            allow_edition = True  # Oculta a opção de busca
        
        # Cria side menu
        if uuid and ('app-admin' in user_groups or 'master' in user_groups or 'sys-admin' in user_groups):
            menu_options.append(menu_url(MENU_USERS_DEFINICAO_ACESSO, url=reverse('user_credential', kwargs={'uuid': associado.uuid})))
    
    associado_dict = {}
    # Garantir que os campos sejam strings vazias se estiverem None
    associado_dict['nome_responsavel'] = associado.nome_responsavel or ''
    associado_dict['aluno'] = associado.aluno or ''
    associado_dict['nome_de_guerra'] = associado.nome_de_guerra or ''
    associado_dict['email'] = associado.email or ''
    associado_dict['nascimento_responsavel'] = f'{associado.nascimento_responsavel:%d/%m/%Y}' if associado.nascimento_responsavel else ''
    associado_dict['cpf'] = associado.cpf or ''
    associado_dict['telefone'] = associado.telefone or ''
    associado_dict['sexo'] = associado.sexo or ''
    associado_dict['nascimento_aluno'] = f'{associado.nascimento_aluno:%d/%m/%Y}' if associado.nascimento_aluno else ''
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
        associado_dict['situacao'] = 'associado.situacao or '''   
        associado_dict['tipo'] = associado.tipo.lower if associado.tipo else ''  

    if request.method == 'POST':
        if convidado:
            # cria registro em branco para novo associado
            associado = tbAssociados()

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

        messages.success(request, "Registro salvo com sucesso!")
        # except Exception as e:
        #     messages.error(request, f"Erro ao salvar registro.\n{str(e)}")
    
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
    }

    return render(request, 'users/user_record.html', context)

@login_required
def user_credential(request, uuid):
    associado = get_object_or_404(tbAssociadosCredentials, uuid=uuid)  # Busca pelo UUID
    user = User.objects.filter(username=associado.codigo_associado).first()
    groups = Group.objects.all()
    user_group_id = user.groups.first().id if user and user.groups.exists() else None
    menu_options = [MENU_VOLTAR]

    allow_edition = False  # Inicializa a opção de busca como visível

    if request.user.is_authenticated:
        is_admin = request.user.groups.filter(name="app-admin").exists() \
                  or request.user.groups.filter(name="master").exists() \
                  or request.user.groups.filter(name="sys-admin").exists() 
        
        if is_admin:
            # Usuários com acesso admin verão todos os registros
            allow_edition = True  # Oculta a opção de busca


    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = uuid
        password = request.POST.get('password')
        group_id = request.POST.get('group')

        # Criar ou atualizar o usuário
        if not user:
            user = User.objects.create(username=username)
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        if password:
            user.set_password(password)
        user.save()

        # Atualizar o grupo do usuário
        group = Group.objects.get(id=group_id)
        user.groups.clear()
        user.groups.add(group)

        messages.success(request, "Credenciais atualizadas com sucesso!")
        return redirect('home')

    return render(request, 'users/user_credential.html', {
        'user': user,
        'associado': associado,
        'groups': groups,
        'user_group_id': user_group_id,
        'allow_edition': allow_edition,
        'menu_options': menu_options,
    })