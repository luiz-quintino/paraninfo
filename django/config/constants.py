MONTHS = {
    1:'JANEIRO', 
    2:'FEVEREIRO', 
    3:'MARÇO', 
    4:'ABRIL', 
    5:'MAIO', 
    6:'JUNHO', 
    7:'JULHO', 
    8:'AGOSTO', 
    9:'SETEMBRO', 
    10:'OUTUBRO',
    11:'NOVEMBRO', 
    12:'DEZEMBRO'
          }

MESSAGE_TYPE_WARNING = 'warning'
MESSAGE_TYPE_INFO = 'info'
MESSAGE_TYPE_ERROR = 'error'
MESSAGE_TYPE_CONFIRM = 'confirm'    # Yes or No
MESSAGE_TYPE_INPUT = 'input'        # Input text
MESSAGE_TYPE_SUCCESS = 'success'

# Não realiza a congruência do mês atual vs tbComissao para o fechamento mensal em close_balance_view()
SKIP_MONTH_CHECK = True
# Não envia email de notificação para associado após o fechamento mensal
SKIP_EMAIL_NOTIFICATION_AFTER_CLOSE_BALANCE = True
# Envia somente email de teste
SEND_ALL_EMAILS = True

# Seleção de registos para realiar o cálculo do valor extra para coto de lsttransacao
FIELDS_USED_FOR_COTA = ['Doação recebida', 'Arrecadação de Eventos', 'Rendimento aplicação']

# Indice para registrar o valor da última diferença de cota
FIELD_COTA_ID = 40