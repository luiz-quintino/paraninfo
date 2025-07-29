from django.shortcuts import render
from config.menus import MENU_AJUDA

def home_view(request):
    # Verificar o grupo do usuário
    user_groups = request.user.groups.values_list('name', flat=True) if request.user.is_authenticated else []
    # Obter a página atual
    current_page = request.resolver_match.url_name if request.resolver_match else None
    # Definir as opções do menu com base no grupo e na página atual
    menu_options = [MENU_AJUDA]


    # verifica todas as requisições
    print("Requisições do usuário: ---------------------------------")
    for req in request.__dict__.items():
        if type(req[1]) == dict:
            print(f"{req[0]}:")
            for key, value in req[1].items():
                print(f"   [{key}]: {value}")
        else:
            print(f"{req[0]}: {req[1]}")

    if request.user.is_authenticated:
        # Divide o nome em partes e define o apelido
        name_parts = request.user.first_name.split(" ")
        if len(name_parts[0]) < 5 and len(name_parts) > 1:
            apelido = f"{name_parts[0]} {name_parts[1]}"
        else:
            apelido = name_parts[0]
        
        # Armazena o apelido e o UUID na sessão
        request.session['apelido'] = apelido
        request.session['user_uuid'] = request.user.last_name

    else:
        # Define valores padrão para usuários não autenticados
        request.session['apelido'] = "Entrar"

    # Passar as opções do menu no contexto
    context = {
        'menu_options': menu_options,
    }

    # Passa a variável is_admin para o template
    return render(request, 'home.html', context)
