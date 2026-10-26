from django.db import models
from paraninfo_admin.models import tbComissao

class tbRelatorio(models.Model):
    id = models.AutoField(primary_key=True)  # Campo automático
    sequencia = models.IntegerField()
    arquivo = models.CharField(max_length=255, null=True, blank=True)  # Campo comissão
    pasta = models.CharField(max_length=255, null=True, blank=True)  # Campo CNPJ
    data = models.DateTimeField()

    comissao = models.ForeignKey(
        tbComissao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comossao'
    )

    class Meta:
        db_table = 'tbrelatorio'
