from users.models import tbAssociados
from paraninfo_admin.models import tbComissao
from home.models import tbSessao  # Importar o modelo tbSessao
import requests

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_location_from_ip( ip):
    region = {"ip": ip,
        "city": None,
        "region": None,
        "country": None,
        "latitude": None,
        "longitude": None
    }

    if ip:
        response = requests.get(f"https://ipapi.co/{ip}/json/")
        if response.status_code == 200:
            data = response.json()
            region = {"ip": ip,
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country_name"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),}
        
    return f"{region['city']}/{region['country']}"


class PersistentUserDataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Verificar se os dados já estão na sessão
            if 'user_data' not in request.session:
                try:
                    associado = tbAssociados.objects.get(uuid=request.user.last_name)
                    comissao = tbComissao.objects.filter(id=associado.comissao).first()
                    groups = list(request.user.groups.values_list('name', flat=True))

                    # Registra a sessão do usuário no banco de dados
                    ip = get_client_ip(request)
                    print(f"IP do usuário: {ip}")
                    print(f'Região do usuário: {get_location_from_ip(ip)}')
                    sessao = tbSessao.objects.create(
                        usuario_id=associado.id,
                        auth_group_id=groups,
                        usuario_ip = ip,
                        localizacao=get_location_from_ip(ip).get('region', 'Desconhecido')
                    )

                    # Atualiza os dados do usuário na sessão
                    request.session['user_data'] = {
                        'sessao_id': sessao.id,  # Armazena o ID da sessão
                        'comissao': associado.comissao,
                        'user_uuid': associado.uuid,
                        'user_id': associado.id,
                        'comissao_title': comissao.comissao if comissao else None,
                        'groups': groups,
                        'is_sys_admin': 'sys-admin' in groups,
                        'is_app_admin': 'app-admin' in groups,
                        'is_master': 'master' in groups,
                        'is_staff': 'staff' in groups,
                        'is_admin': any(group in groups for group in ['sys-admin', 'app-admin', 'master']),
                    }

                except tbAssociados.DoesNotExist:
                    pass

                print('dados do usuário atualizados na sessão')
                ip = get_client_ip(request)
                print(f"IP do usuário: {ip}")

            # Atualiza os atributos do request com os dados da sessão
            user_data = request.session['user_data']

            for key, value in user_data.items():
                setattr(request, key, value)


        else:
            print('usuário não logado')
            # Limpar os dados da sessão para usuários não autenticados
            request.session.pop('user_data', None)
            for key in ['comissao', 'user_id', 'user_uuid', 'comissao_title', 'user_groups', 
                        'is_sys_admin', 'is_app_admin', 'is_master', 'is_staff', 'is_admin', 'sesssao']:
                setattr(request, key, None if key != 'user_groups' else [])

        response = self.get_response(request)
        print('response', response)
        return response