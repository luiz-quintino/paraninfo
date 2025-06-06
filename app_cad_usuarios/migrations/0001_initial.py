# Generated by Django 5.2.1 on 2025-06-01 14:34

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Usuarios",
            fields=[
                (
                    "id_usuario",
                    models.AutoField(
                        primary_key=True, serialize=False, verbose_name="ID do Usuário"
                    ),
                ),
                ("nome", models.TextField(max_length=100, verbose_name="Nome")),
                ("idade", models.IntegerField(verbose_name="Idade")),
            ],
            options={
                "verbose_name": "Usuários",
                "verbose_name_plural": "Usuários",
                "ordering": ["nome"],
            },
        ),
    ]
