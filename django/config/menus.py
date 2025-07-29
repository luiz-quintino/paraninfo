

# Menu principal

def menu_url(menu: dict, url: str) -> dict:
    menu['url']= url
    return menu


# type: form | url
MENU_AJUDA                              = {'name': 'Ajuda',                       
                                           'url': "#",
                                           'tip': 'Acesse a documentação do sistema',}

MENU_VOLTAR                             = {'name': 'Voltar',                      
                                           'url': '#',                   
                                           'type': 'voltar',
                                           'tip': 'Voltar para a página anterior',
                                           'color': '#4caf50',}

MENU_USERS_INCLUIR_USUARIO              = {'name': 'Incluir usuário',             
                                           'url': '/users/user-record',
                                           'tip': 'Acesse o formulário para inclusão de um novo usuário'}

MENU_USERS_GERAR_CONVITE                = {'name': 'Gerar convite',               
                                           'url': '#',
                                           'tip': 'Acesse o formulário para gerar um convite para um novo usuário'}

MENU_USERS_DEFINICAO_ACESSO             = {'name': 'Definição de acesso',         
                                           'url': '#',
                                           'tip': 'Acesse o formulário para definir o acesso de um usuário'}

MENU_CLIENTS_INCLUIR_COMISSAO           = {'name': 'Incluir comissão',            
                                           'url': '/paraninfo-admin/client-details',
                                           'tip': 'Acesse o formulário para inclusão de uma nova comissão'}

MENU_BALANCE_EXTRATO                    = {'name': 'Menu movimentações',                     
                                           'url': "/transaction",
                                           'tip': 'Acesse o menu de extratos para visualizar, importar e analisar movimentações financeiras',
                                           'color': '#b5e2fa',}

MENU_BALANCE_IMPORTAR_EXTRATO           = {'name': 'Importar novo extrato',       
                                           'url': "/transaction",
                                           'tip': 'Acesse o formulário para importar um novo extrato bancário'}

MENU_BALANCE_ENTRADA_MANUAL             = {'name': 'Entrada manual',              
                                           'url': "/transaction/entrada-manual",
                                           'tip': 'Acesse o formulário para entrada manual de movimentações financeiras'}

MENU_BALANCE_ANALISAR_MOVIMENTACAO      = {'name': 'Analisar movimentação',       
                                           'url': "analise-movimentacao", 
                                           'type': 'js', 
                                           'function': 'openAnalisePage()',
                                           'tip': 'Acesse o formulário para analisar movimentações financeiras'}

MENU_BALANCE_INCORPORAR_MOVIMENTACAO    = {'name': 'Aceitar movimentação',     
                                           'url': "#",
                                           'tip': 'Acesse o formulário para aceitar movimentações financeiras'}

MENU_BALANCE_ACEITAR_EXTRATO            = {'name': 'Aceitar extrato',             
                                           'url': "aceitar_extrato",      
                                           'type': 'js', 
                                           'function': 'submitEntradaForm()',               
                                           'color': 'yellow',
                                           'tip': 'Aceitar o extrato bancário importado para análise'}

MENU_BALANCE_ACEITAR_ENTRADAS_EXTRATO   = {'name': 'Aceitar entradas de extrato', 
                                           'url': "importacao",           
                                           'type': 'js', 
                                           'function': 'submitImportacaoForm()',
                                           'tip': 'Aceitar as entradas de extrato bancário importadas para análise',}

MENU_BALANCE_SALVAR_MOVIMENTACOES       = {'name': 'Salvar movimentação',         
                                           'url': "analise-movimentacao", 
                                           'type': 'js', 
                                           'function': 'submitForm("formAnalise")',         
                                           'color': 'yellow',
                                           'tip': 'Salvar as análises de movimentações financeiras realizadas'}

MENU_BALANCE_REVISAR_ANALISE            = {'name': 'Revisar análise',             
                                           'url': "analise-movimentacao", 
                                           'type': 'js', 
                                           'function': 'submitForm("formRevisao")',
                                           'tip': 'Revisar as análises de movimentações financeiras realizadas'}

MENU_BALANCE_FECHAR_ANALISE             = {'name': 'Concluir análise',              
                                           'url': "analise-movimentacao", 
                                           'type': 'js', 
                                           'function': 'submitForm("formFechamento")',
                                           'tip': 'Fechar a análise de movimentações financeiras realizadas',
                                           'color': 'yellow',}

MENU_BALANCE_FECHAR_ANALISE_CONFIRMAR   = {'name': 'Confirmar fechamento',        
                                           'url': "analise-movimentacao", 
                                           'type': 'js', 
                                           'function': 'submitForm("formConfirmarFechamento")',
                                           'tip': 'Confirmar o fechamento da análise de movimentações financeiras realizadas'}

MENU_CONTABILIDADE_VER_EXTRATO          = {'name': 'Extrato de movimentações',
                                           'url': "", 
                                           'tip': 'Acesse o extrato para visualizar as movimentações financeiras'}

MENU_CONTABILIDADE_FECHAR_BALANCO       = {'name': 'Fechar balanço mensal',
                                           'url': "balance/fechar-balanco", 
                                           'tip': 'Fechar o balanço contábil para o período selecionado',
                                           'color': 'yellow'}

MENU_CONTABILIDADE_RESUMO_OPERACOES     = {'name': 'Resumo de operações',
                                            'url': "contabilidade/resumo-operacoes",
                                            'tip': 'Acesse o resumo de operações para visualizar as movimentações financeiras resumidas'}

MENU_CONTABILIDADE_LIVRO_CAIXA          = {'name': 'Livro caixa',
                                           'url': "contabilidade/livro-caixa",
                                           'tip': 'Acesse o livro caixa para visualizar as movimentações financeiras registradas'}

MENU_CONTABILIDADE_MENSALIDADDES        = {'name': 'Mensalidades',
                                           'url': "contabilidade/mensalidades",
                                           'tip': 'Acesse as mensalidades para visualizar as movimentações financeiras mensais'}

MENU_CONTABILIDADE_EMITIR_RECIBOS       = {'name': 'Emitir recibos',
                                           'url': "contabilidade/emitir-recibos",
                                           'tip': 'Acesse o formulário para emitir recibos de pagamentos realizados'}

MENU_CONTABILIDADE_INADIMPLENTES        = {'name': 'Inadimplentes',
                                            'url': "contabilidade/inadimplentes",
                                            'tip': 'Acesse a lista de inadimplentes para visualizar os associados com pendências financeiras'}

MENU_CONTABILIDADE_EMITIR_COBRANCA      = {'name': 'Emitir cobrança',
                                           'url': "contabilidade/emitir-cobranca",
                                           'tip': 'Acesse o formulário para emitir cobranças para associados inadimplentes'}

MENU_CONTABILIDADE_ASSINAR_LIVRO_CAIXA  = {'name': 'Assinar livro caixa',
                                           'url': "contabilidade/assinar-livro-caixa",
                                           'tip': 'Acesse o formulário para assinar o livro caixa'}