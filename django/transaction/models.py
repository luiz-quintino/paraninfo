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

class tbResumoComissao(models.Model):   
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    comissao_id = models.IntegerField(null=True, blank=False)
    mes_corrente = models.IntegerField(null=True, blank=False)
    ano_corrente = models.IntegerField(null=True, blank=False)
    sequencia = models.IntegerField(null=True, blank=False)
    valor_mensalidade = models.FloatField(null=True, blank=False)
    valor_mensalidade_reajuste = models.FloatField(null=True, blank=False)
    valor_cota = models.FloatField(null=True, blank=False)
    valor_objetivo_mensalidade = models.FloatField(null=True, blank=False)
    saldo_total = models.FloatField(null=True, blank=False)
    saldo_total_aplicado = models.FloatField(null=True, blank=False)
    valor_taxa_boleto = models.FloatField(null=True, blank=False)

    class Meta:
        db_table = 'tbResumoComissao'

class tbResumoAssociado(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    mensalidades_pagas = models.IntegerField(null=True, blank=True)
    valor_pago = models.FloatField(null=True, blank=True)
    valor_em_aberto = models.FloatField(null=True, blank=True)
    valor_credito = models.FloatField(null=True, blank=True)
    valor_outros = models.FloatField(null=True, blank=True)
    valor_acordo = models.FloatField(null=True, blank=True)

    # Relacionamento com tbAssociado
    associado = models.ForeignKey(
        tbAssociados,   
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resumo_associado'
    )

    class Meta:
        db_table = 'tbResumoAssociado'




class tbBoletoStatus(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    status = models.CharField(max_length=15, null=True, blank=False)

    class Meta:
        db_table = 'tbBoletoStatus'  # Nome da tabela no banco de dados


class tbBoleto(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    data = models.DateField(max_length=8, null=True, blank=False)
    comissao_id = models.IntegerField(null=True, blank=False)
    seu_numero = models.CharField(max_length=10, null=True, blank=False)
    nosso_numero = models.CharField(max_length=20, null=True, blank=False)
    valor_boleto = models.FloatField(null=True, blank=False)
    valor_pg = models.FloatField(null=True, blank=False)
    dt_vencimento = models.DateField(max_length=8, null=True, blank=False)
    dt_pagamento = models.DateField(max_length=8, null=True, blank=False)
    log_criacao_id = models.IntegerField(null=True, blank=True)
    log_status_id = models.IntegerField(null=True, blank=True)
    mensagem = models.CharField(max_length=45, null=True, blank=True)

    # Relacionamento com tbAssociado
    associado = models.ForeignKey(
        tbAssociados,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boletos'
    )   

    # Relacionamento com tbBoletoStatus
    boleto_status = models.ForeignKey(
        tbBoletoStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boleto_status'
    )

    class Meta:
        db_table = 'tbBoleto'


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

