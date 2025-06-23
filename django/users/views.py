from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import LoginView
import uuid as uuid_generate # Certifique-se de que o módulo uuid está importado corretamente
from django.utils.timezone import localtime, timezone, get_current_timezone

from users.models import tbAssociados, tbAssociadosListView, tbAssociadosCredentials

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
    search_query = request.GET.get('search', '')  # Obtém o texto do filtro
    associados = tbAssociadosListView.objects.only(
        'codigo_associado', 'nome_responsavel', 'aluno', 'nome_de_guerra'
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
    else:
        associados = tbAssociadosListView.objects.none()  # Retorna uma lista vazia para usuários não autenticados

    # Paginação: 10 registros por página
    paginator = Paginator(associados, 10)
    page_number = request.GET.get('page')
    associados_page = paginator.get_page(page_number)

    return render(request, 'users/user_list.html', {
        'associados': associados_page,
        'show_search': show_search,
    })

@login_required()
def user_record(request, uuid=None):
    if uuid:
        print(f"UUID fornecido: {uuid}")
        # Busca o registro pelo UUID
        associado = get_object_or_404(tbAssociados, uuid=uuid)  # Busca pelo UUID
        allow_edition = False  # Inicializa a opção de busca como visível
    else:
        print("Nenhum UUID fornecido, criando um novo registro.")
        # Cria um registro vazio para adição
        associado = tbAssociados()


    if request.user.is_authenticated:
        is_admin = request.user.groups.filter(name="app-admin").exists() \
                  or request.user.groups.filter(name="master").exists() \
                  or request.user.groups.filter(name="sys-admin").exists() 
        
        if is_admin:
            # Usuários com acesso admin verão todos os registros
            allow_edition = True  # Oculta a opção de busca

   # Garantir que os campos sejam strings vazias se estiverem None
    associado.codigo_associado = associado.codigo_associado or ''
    associado.nome_responsavel = associado.nome_responsavel or ''
    associado.aluno = associado.aluno or ''
    associado.nome_de_guerra = associado.nome_de_guerra or ''
    associado.codigo_pagamento = associado.codigo_pagamento or ''
    associado.email = associado.email or ''
    associado.nascimento_responsavel = associado.nascimento_responsavel or ''
    associado.cpf = associado.cpf or ''
    associado.telefone = associado.telefone or ''
    associado.sexo = associado.sexo or ''
    associado.nascimento_aluno = associado.nascimento_aluno or ''
    associado.matricula = associado.matricula or ''
    associado.endereco = associado.endereco or ''  
    associado.numero = associado.numero or ''  
    associado.complemento = associado.complemento or ''  
    associado.bairro = associado.bairro or ''  
    associado.cidade = associado.cidade or ''  
    associado.cep = associado.cep or ''  
    associado.tipo = associado.tipo or ''  
    associado.situacao = associado.situacao or ''     

    if request.method == 'POST':
        try:
            # Gera um UUID apenas para novos registros
            if not uuid:
                associado.uuid = str(uuid_generate.uuid4())
                associado.data = localtime(get_current_timezone()).strftime('%d-%m-%y %H:%M')  # Formata a data
                associado.codigo_associado = f"{request.comissao:02}{request.POST.get('matricula')}{request.POST.get('codigo_pagamento')}"

            if not request.POST.get('comissao'):
                associado.comissao = request.comissao
            else:
                associado.comissao = request.POST.get('comissao')
            
            associado.nome_responsavel = request.POST.get('nome_responsavel')
            associado.aluno = request.POST.get('aluno')
            associado.nome_de_guerra = request.POST.get('nome_de_guerra')
            associado.codigo_pagamento = request.POST.get('codigo_pagamento')
            associado.email = request.POST.get('email')
            associado.nascimento_responsavel = request.POST.get('nascimento_responsavel')
            associado.cpf = request.POST.get('cpf')
            associado.telefone = request.POST.get('telefone')
            associado.sexo = request.POST.get('sexo')
            associado.nascimento_aluno = request.POST.get('nascimento_aluno')
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
        except Exception as e:
            messages.error(request, f"Erro ao salvar registro.\n{str(e)}")

    return render(request, 'users/user_record.html', {'associado': associado, 'allow_edition': allow_edition, 'uuid': uuid})

@login_required
def user_credential(request, uuid):
    associado = get_object_or_404(tbAssociadosCredentials, uuid=uuid)  # Busca pelo UUID
    user = User.objects.filter(username=associado.codigo_associado).first()
    groups = Group.objects.all()
    user_group_id = user.groups.first().id if user and user.groups.exists() else None

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
        'allow_edition': allow_edition
    })