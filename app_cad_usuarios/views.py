from django.shortcuts import render
from .models import Usuario

# Create your views here.

def home(request):
    """
    Função responsável por renderizar a página inicial do sistema.
    """
    
    return render(request, 'usuarios/home.html')

def usuarios(request):
    """Função responsável por renderizar a página de listagem de usuários.
    """
    
    # Salva dados usuários no banco de dados
    if request.method == 'POST':
        nome = request.POST.get('nome', None)
        idade = request.POST.get('idade', None)

        print(f"Dados recebidos - Nome: {nome}, Idade: {idade}")  # Exibe os dados recebidos no console
        
        if nome and idade:  # Verifica se os dados foram enviados
            try:
                novo_usuario = Usuario(nome=nome, idade=int(idade))
                print(f"Objeto criado - Nome: {novo_usuario.nome}, Idade: {novo_usuario.idade}")  # Exibe o objeto criado
                novo_usuario.save()
                print("Usuário salvo com sucesso!")  # Confirmação de salvamento
            except ValueError as e:
                print(f"Erro ao salvar usuário: {e}")  # Exibe o erro no console
            except Exception as e:
                print(f"Erro inesperado: {e}")  # Captura outros erros inesperados
    
    usuarios = {
        'usuarios': Usuario.objects.all()
        #'nome': novo_usuario.nome,
        #'idade': novo_usuario.idade
    }

    return render(request, 'usuarios/usuarios.html', usuarios)
    
    