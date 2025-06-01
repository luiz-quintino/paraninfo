from django.db import models

class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True, verbose_name='ID do Usuário') 
    nome = models.TextField(max_length=100)
    idade = models.IntegerField()

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nome']