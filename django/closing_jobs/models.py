from django.db import models


class BalanceClosingJob(models.Model):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCEEDED = 'succeeded'
    COMPLETED_WITH_WARNINGS = 'completed_with_warnings'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, 'Pendente'),
        (RUNNING, 'Em execução'),
        (SUCCEEDED, 'Concluído'),
        (COMPLETED_WITH_WARNINGS, 'Concluído com avisos'),
        (FAILED, 'Falhou'),
    ]

    comissao_id = models.IntegerField()
    requested_by_user_id = models.IntegerField()
    session_id = models.IntegerField(default=0)
    year = models.IntegerField()
    month = models.IntegerField()
    sequence = models.IntegerField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=PENDING)
    message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'balance_closing_job'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='bal_close_job_status_idx'),
            models.Index(fields=['comissao_id', 'status'], name='bal_close_job_comm_idx'),
        ]

    def __str__(self):
        return f'Fechamento {self.comissao_id} {self.month}/{self.year} ({self.status})'
