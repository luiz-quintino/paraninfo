import uuid
from django.contrib.auth.models import User
from django.db import models


class tbAssociados(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.CharField(max_length=36, unique=True, default=uuid.uuid4)  # Campo UUID

    # Campos da tabela
    data = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    nome_responsavel = models.CharField(max_length=255, null=True, blank=True)
    nascimento_responsavel = models.CharField(max_length=8, null=True, blank=True)
    cpf = models.CharField(max_length=14, null=True, blank=True)
    telefone = models.CharField(max_length=15, null=True, blank=True)
    aluno = models.CharField(max_length=38, null=True, blank=True)
    nome_de_guerra = models.CharField(max_length=30, null=True, blank=True)
    sexo = models.CharField(max_length=9, null=True, blank=True)
    nascimento_aluno = models.CharField(max_length=8, null=True, blank=True)
    matricula = models.CharField(max_length=4, null=True, blank=True)
    endereco = models.CharField(max_length=36, null=True, blank=True)
    numero = models.CharField(max_length=4, null=True, blank=True)
    complemento = models.CharField(max_length=23, null=True, blank=True)
    bairro = models.CharField(max_length=16, null=True, blank=True)
    cidade = models.CharField(max_length=14, null=True, blank=True)
    cep = models.CharField(max_length=10, null=True, blank=True)
    tipo = models.CharField(max_length=19, null=True, blank=True)
    situacao = models.CharField(max_length=7, null=True, blank=True)
    codigo_pagamento = models.CharField(max_length=5, null=True, blank=True)
    codigo_associado = models.CharField(max_length=6, null=True, blank=True)
    certificado = models.CharField(max_length=10, null=True, blank=True)
    kit = models.CharField(max_length=10, null=True, blank=True)
    inscricao = models.CharField(max_length=8, null=True, blank=True)
    comissao = models.IntegerField(null=False, blank=False)  # Referência a outra tabela (comissão)

    def __str__(self):
        return self.nome_responsavel or "Sem Nome"

    class Meta:
        db_table = 'tbAssociados'  # Define explicitamente o nome da tabela

class tbAssociadosListView(tbAssociados):
    """
    Modelo proxy para exibir apenas os campos necessários na página user_list.
    """
    class Meta:
        proxy = True
        verbose_name = "Associado (Listagem)"
        verbose_name_plural = "Associados (Listagem)"

class tbAssociadosCredentialsManager(models.Manager):
    def get_queryset(self):
        # Retorna apenas os campos especificados
        return super().get_queryset().only(
            'nome_responsavel', 'aluno', 'codigo_associado', 'email'
        )

class tbAssociadosCredentials(tbAssociados):
    """
    Classe proxy para tbAssociados, exibindo apenas os campos necessários.
    """
    objects = tbAssociadosCredentialsManager()

    class Meta:
        proxy = True
        verbose_name = "Credencial do Associado"
        verbose_name_plural = "Credenciais dos Associados"