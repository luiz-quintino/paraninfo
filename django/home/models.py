from django.db import models
from users.models import tbAssociados

class tbSessao(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    data = models.DateTimeField(auto_now_add=True)  # Campo de data com valor padrão como a data atual
    # usuario_id = models.IntegerField()  # Relacionamento com o modelo User
    auth_group_id = models.CharField(max_length=45)  # Campo varchar com limite de 45 caracteres
    usuario_ip = models.CharField(max_length=45, null=True, blank=True)  # Campo para armazenar o IP do usuário
    localizacao = models.CharField(max_length=45, null=True, blank=True)  # Campo para armazenar a localização do usuário

    # Relacionamento com tbTransacao
    usuario = models.ForeignKey(
        tbAssociados,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user'
    )

    class Meta:
        db_table = 'tbSessao'  # Nome da tabela no banco de dados

    def __str__(self):
        return f"{self.id} - {self.data}"
    
class tbLog(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    data = models.DateTimeField(auto_now_add=True)  # Campo de data com valor padrão como a data atual
    pagina_id = models.IntegerField()  # Campo inteiro para identificar a página
    evento_log_id = models.IntegerField()  # Campo inteiro para identificar o evento
    sessao_ativa_id = models.IntegerField()  
    descricao = models.CharField(max_length=45)

    class Meta:
        db_table = 'tbLog'  # Nome da tabela no banco de dados

    def __str__(self):
        return f"{self.id} - {self.data} - Página: {self.pagina_id} - Evento: {self.evento_id}"
    
class tbPagina(models.Model):
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    pagina = models.CharField(max_length=45)  # Campo varchar com limite de 45 caracteres

    class Meta:
        db_table = 'tbPagina'  # Nome da tabela no banco de dados

    def __str__(self):
        return f"{self.id} - {self.pagina}"
    