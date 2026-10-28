from django.db import models


class tbEmail(models.Model):
    data = models.DateTimeField(auto_now_add=True)
    titulo = models.CharField(max_length=45)
    conteudo = models.CharField(max_length=255)
    distribuicao = models.CharField(max_length=255)
    log_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'tbemail'
        ordering = ['-data']
