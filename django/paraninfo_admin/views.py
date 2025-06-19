from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from paraninfo_admin.models import tbComissao
import uuid as uuid_generate # Certifique-se de que o módulo uuid está importado corretamente

uuid = ''

# Função para verificar se o usuário pertence ao grupo 'sys_admin'
def is_sys_admin(user):
    return user.groups.filter(name='sys-admin').exists()

@user_passes_test(is_sys_admin)
def client_details(request, uuid=None):
    if uuid:
        # Busca o registro pelo UUID
        comissao = get_object_or_404(tbComissao, uuid=uuid)
    else:
        # Cria um registro vazio para adição
        comissao = tbComissao()

    # Garantir que os campos sejam strings vazias se estiverem None
    comissao.comissao = comissao.comissao or ''
    comissao.cnpj = comissao.cnpj or ''
    comissao.inscricao = comissao.inscricao or ''
    comissao.endereco = comissao.endereco or ''
    comissao.cep = comissao.cep or ''
    comissao.imagem = comissao.imagem or ''
    comissao.presidente = comissao.presidente or 1

    if request.method == 'POST':
        try:
            # Gera um UUID apenas para novos registros
            if not uuid:
                comissao.uuid = str(uuid_generate.uuid4())
                
            # Atualiza ou salva os dados do registro
            comissao.comissao = request.POST.get('comissao')
            comissao.cnpj = request.POST.get('cnpj')
            comissao.inscricao = request.POST.get('inscricao')
            comissao.endereco = request.POST.get('endereco')
            comissao.imagem = request.POST.get('imagem')
            comissao.presidente = request.POST.get('presidente')
            comissao.cep = request.POST.get('cep')
            comissao.save()

            messages.success(request, "Registro salvo com sucesso!")

            # Redireciona para a página de detalhes do cliente com o UUID
            return redirect('client_details', uuid=comissao.uuid)
        except Exception as e:
            print('erro', str(e))
            messages.error(request, f"Erro ao salvar registro: {str(e)}")

    return render(request, 'paraninfo_admin/client_details.html', {'comissao': comissao, 'uuid': uuid})

@user_passes_test(is_sys_admin)
def client_list(request):
    search_query = request.GET.get('search', '')  # Obtém o texto de busca
    clients = tbComissao.objects.all()  # Obtém todos os registros da tabela tbComissao

    if search_query:
        # Filtrar os registros com base no texto de busca
        clients = clients.filter(
            comissao__icontains=search_query
        ) | clients.filter(
            cnpj__icontains=search_query
        ) | clients.filter(
            inscricao__icontains=search_query
        ) | clients.filter(
            endereco__icontains=search_query
        ) | clients.filter(
            presidente__icontains=search_query
        )

    return render(request, 'paraninfo_admin/client_list.html', {'clients': clients, 'search_query': search_query})
