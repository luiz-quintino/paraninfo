from django.shortcuts import render


def home_view(request):
    is_admin = False  # Inicializa a variável para verificar o grupo
    is_sys_admin = False
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

        # Verifica se o usuário pertence ao grupo "app-admin"
        is_admin = request.user.groups.filter(name="app-admin").exists()
        is_master = request.user.groups.filter(name="master").exists()
        is_staff = request.user.groups.filter(name="staff").exists()
        is_sys_admin = request.user.groups.filter(name="sys-admin").exists()
        is_user = request.user.groups.filter(name="user").exists()
        access_type = {
            'is_admin': is_admin,
            'is_master': is_master,
            'is_staff': is_staff,
            'is_sys_admin': is_sys_admin,
            'is_user': is_user,
        }
    else:
        # Define valores padrão para usuários não autenticados
        request.session['apelido'] = "Entrar"
        access_type = {
            'is_admin': False,
            'is_master': False,
            'is_staff': False,
            'is_sys_admin': False,
            'is_user': False,
        }

    # Passa a variável is_admin para o template
    return render(request, 'home.html', access_type)
