from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='BalanceClosingJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comissao_id', models.IntegerField()),
                ('requested_by_user_id', models.IntegerField()),
                ('session_id', models.IntegerField(default=0)),
                ('year', models.IntegerField()),
                ('month', models.IntegerField()),
                ('sequence', models.IntegerField()),
                ('status', models.CharField(choices=[('pending', 'Pendente'), ('running', 'Em execução'), ('succeeded', 'Concluído'), ('completed_with_warnings', 'Concluído com avisos'), ('failed', 'Falhou')], default='pending', max_length=32)),
                ('message', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'balance_closing_job',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='balanceclosingjob',
            index=models.Index(fields=['status', 'created_at'], name='bal_close_job_status_idx'),
        ),
        migrations.AddIndex(
            model_name='balanceclosingjob',
            index=models.Index(fields=['comissao_id', 'status'], name='bal_close_job_comm_idx'),
        ),
    ]
