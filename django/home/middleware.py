from users.models import tbAssociados
from paraninfo_admin.models import tbComissao  # Certifique-se de que o modelo tbComissao está definido corretamente

class PersistentUserDataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Busca o associado com base no usuário logado
                associado = tbAssociados.objects.get(uuid=request.user.last_name)
                request.comissao = associado.comissao
                request.user_uuid = associado.uuid

                # Busca o título da comissão com base no ID da comissão
                try:
                    comissao = tbComissao.objects.get(id=associado.comissao)
                    request.comissao_title = comissao.comissao
                except tbComissao.DoesNotExist:
                    request.comissao_title = None
                
                # Adiciona os grupos do usuário ao request
                groups = list(request.user.groups.values_list('name', flat=True))
                request.is_sys_admin = 'sys-admin' in groups
                request.is_app_admin = 'app-admin' in groups
                request.is_master = 'master' in groups
                request.is_staff = 'staff' in groups
                request.is_admin = request.is_sys_admin | request.is_app_admin | request.is_master

            except tbAssociados.DoesNotExist:
                request.comissao = None
                request.user_uuid = None
                request.comissao_title = None
                request.user_groups = []
                request.is_sys_admin = False
                request.is_admin = False
                request.is_app_admin = False
                request.is_master = False
                request.is_staff = False
                
        else:
            request.comissao = None
            request.user_uuid = None
            request.comissao_title = None
            request.user_groups = []
            request.is_sys_admin = False
            request.is_admin = False
            request.is_app_admin = False
            request.is_master = False
            request.is_staff = False

        response = self.get_response(request)
        return response