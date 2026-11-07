from django.apps import AppConfig
import sys
import os


class CertificadoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'certificate'

    def ready(self):# Evita execução durante comandos de gerenciamento como migrate, makemigrations, etc.
        if 'runserver' in sys.argv or \
            os.path.basename(sys.argv[0]) == 'gunicorn' or \
            'uwsgi' in sys.argv:
            # Importe sua função aqui dentro para evitar problemas de importação circular
            from .cert_lib.sign_document import intall_root_certificate_and_check_validity

            intall_root_certificate_and_check_validity()
            
            # (Opcional) Adicione uma trava para garantir que rode apenas uma vez 
            # mesmo com o hot-reload do Django ativado em desenvolvimento
            # import os
            # if os.environ.get('RUN_MAIN') == 'true' or 'gunicorn' in sys.argv or 'uwsgi' in sys.argv:
                # executar_na_inicializacao()
