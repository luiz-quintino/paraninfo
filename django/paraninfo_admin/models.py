import uuid
from django.db import models

class tbComissao(models.Model):
    id = models.AutoField(primary_key=True)  # Campo automático
    uuid = models.CharField(max_length=36, unique=True, default=uuid.uuid4)  # Campo UUID
    comissao = models.CharField(max_length=255, null=True, blank=True)  # Campo comissão
    cnpj = models.CharField(max_length=255, null=True, blank=True)  # Campo CNPJ
    inscricao = models.CharField(max_length=255, null=True, blank=True)  # Campo inscrição
    endereco = models.CharField(max_length=255, null=True, blank=True)  # Campo endereço
    cep = models.CharField(max_length=10, null=True, blank=True)  # Campo cep
    imagem = models.CharField(max_length=255, null=True, blank=True)  # Campo imagem
    presidente = models.IntegerField(null=True, blank=True)  # Campo presidente (referência a outro ID)

    def __str__(self):
        return self.comissao or "Sem Comissão"

    class Meta:
        db_table = 'tbComissao'  # Define explicitamente o nome da tabela