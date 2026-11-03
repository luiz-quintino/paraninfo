from django.db import models

# Create your models here.
class tbCertificados(models.Model):
    STATUS_VALIDO = 0
    STATUS_CANCELADO = 1
    STATUS_VENCIDO = 2

    TYPE_ROOT_CA = 'root'
    TYPE_INTERMEDIATE_CA = 'intermediate'
    TYPE_USER_LEAF = 'user'
    
    id = models.AutoField(primary_key=True)
    data = models.DateField(null=True, blank=True)
    tipo = models.CharField(max_length=45, null=True, blank=True)
    senha = models.CharField(max_length=100, null=True, blank=True)
    arquivo = models.CharField(max_length=45)
    validade = models.DateField(null=True, blank=True)
    situacao = models.IntegerField()
    
    class Meta:
        db_table = 'tbcertificados'
        managed = False
