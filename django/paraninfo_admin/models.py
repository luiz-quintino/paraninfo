import uuid
from django.db import models

class lstTipoIdentificacao(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    tipo = models.CharField(max_length=45, null=True, blank=False)  # Descrição do tipo de identificação

    class Meta:
        db_table = 'lstTipoIdentificacao'  # Nome da tabela no banco de dados

class lstTipoBoleto(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    tipo = models.CharField(max_length=45, null=True, blank=False)  # Descrição do tipo de boleto

    class Meta:
        db_table = 'lstTipoBoleto'

class tbComissao(models.Model):
    id = models.AutoField(primary_key=True)  # Campo automático
    uuid = models.CharField(max_length=36, unique=True, default=uuid.uuid4)  # Campo UUID
    nome_comissao = models.CharField(max_length=255, null=True, blank=True)  # Campo comissão
    cnpj = models.CharField(max_length=255, null=True, blank=True)  # Campo CNPJ
    inscricao = models.CharField(max_length=255, null=True, blank=True)  # Campo inscrição
    endereco = models.CharField(max_length=255, null=True, blank=True)  # Campo endereço
    cep = models.CharField(max_length=10, null=True, blank=True)  # Campo cep
    imagem = models.CharField(max_length=255, null=True, blank=True)  # Campo imagem
    presidente = models.IntegerField(null=True, blank=True)  # Campo presidente (referência a outro ID)
    dia_vencimento = models.IntegerField(null=True, blank=True)  # Campo dia de vencimento
    valor_mensalidade = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Campo valor mensalidade
    valor_mensalidade_reajuste = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Campo valor mensalidade reajuste
    valor_taxa_boleto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Campo valor mensalidade reajuste
    incluir_tx_boleto = models.BooleanField(default=False)  # Campo incluir taxa boleto
    banco = models.CharField(max_length=45, null=True, blank=True)  # Campo banco
    conta = models.CharField(max_length=45, null=True, blank=True)  # Campo conta
    agencia = models.CharField(max_length=45, null=True, blank=True)  # Campo agência
    codigo_banco = models.CharField(max_length=45, null=True, blank=True)  # Campo código do banco
    convite_uuid = models.CharField(max_length=36, null=True, blank=True)  # Campo convite UUID
    convite_log_id = models.IntegerField(null=True, blank=True)  # Campo convite log ID

    # Relacionamento com tbTipo_identificacao
    tipo_identificacao = models.ForeignKey(
        lstTipoIdentificacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tipo_identificacao'
    )

    # Relacionamento com tbTipoBoleto
    tipo_boleto = models.ForeignKey(
        lstTipoBoleto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tipo_boleto'
    )

    def __str__(self):
        return self.comissao or "Sem Comissão"

    class Meta:
        db_table = 'tbComissao'  

    