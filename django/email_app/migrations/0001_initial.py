from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='tbEmail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateTimeField(auto_now_add=True)),
                ('titulo', models.CharField(max_length=45)),
                ('conteudo', models.CharField(max_length=255)),
                ('distribuicao', models.CharField(max_length=255)),
                ('log_id', models.IntegerField(blank=True, null=True)),
            ],
            options={'db_table': 'tbemail', 'ordering': ['-data']},
        ),
    ]
