from django.db import models
from users.models import tbAssociados

class tbTransacao(models.Model):
    key = models.CharField(max_length=45, unique=True)
    value = models.CharField(max_length=45)
    color_name = models.CharField(max_length=45)
    value = models.CharField(max_length=45)


    class Meta:
        db_table = 'tbTransacao'


class tbExtratoConfig(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    descricao = models.CharField(max_length=50, blank=True, null=True)  # Descrição opcional
    condicao = models.CharField(max_length=50, blank=True, null=True)  # Descrição opcional
    configuracao = models.CharField(max_length=50, blank=True, null=True)  # Descrição opcional
    transacao_id = models.IntegerField()

    class Meta:
        db_table = 'tbExtratoConfig'  # Nome da tabela no banco de dados


class tbExtrato(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    comissao_id = models.IntegerField(null=True, blank=False)
    data = models.DateField(max_length=8, null=True, blank=False)
    documento = models.CharField(max_length=45, null=True, blank=False)
    historico = models.CharField(max_length=255)
    credito = models.FloatField(null=True, blank=True)
    debito = models.FloatField(null=True, blank=True)
    tipo = models.CharField(max_length=45, null=True, blank=True)
    nome = models.CharField(max_length=45, null=True, blank=True)
    nota = models.CharField(max_length=255, null=True, blank=True)
    cpf = models.CharField(max_length=45, null=True, blank=True)
    saldo = models.FloatField(null=True, blank=True)
    status = models.IntegerField(null=True, blank=True)
    # transacao_id = models.IntegerField(null=True, blank=True)
    # associado_id = models.IntegerField(null=True, blank=True)
    log_registro_id = models.IntegerField(null=True, blank=True)
    log_associacao_id = models.IntegerField(null=True, blank=True)
    log_fechamento_id = models.IntegerField(null=True, blank=True)

    # Relacionamento com tbTransacao
    transacao = models.ForeignKey(
        tbTransacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacao'
    )
    # Relacionamento com tbAssociado
    associado = models.ForeignKey(
        tbAssociados,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='associado'
    )



    class Meta:
        db_table = 'tbExtrato'
