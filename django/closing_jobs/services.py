from django.db import transaction

from paraninfo_admin.models import tbComissao

from .models import BalanceClosingJob


ACTIVE_STATUSES = (BalanceClosingJob.PENDING, BalanceClosingJob.RUNNING)


def enqueue_balance_closing(comissao_id, requested_by_user_id, session_id):
    """Create one durable close job per commission/month and prevent duplicates."""
    with transaction.atomic():
        comissao = (
            tbComissao.objects.select_for_update()
            .filter(id=comissao_id)
            .first()
        )
        if comissao is None:
            raise tbComissao.DoesNotExist

        active_job = (
            BalanceClosingJob.objects.select_for_update()
            .filter(comissao_id=comissao_id, status__in=ACTIVE_STATUSES)
            .order_by('-created_at')
            .first()
        )
        if active_job:
            return active_job, False

        existing_period_job = (
            BalanceClosingJob.objects.select_for_update()
            .filter(
                comissao_id=comissao_id,
                year=comissao.ano,
                month=comissao.mes,
                sequence=comissao.sequence,
            )
            .order_by('-created_at')
            .first()
        )
        if existing_period_job:
            return existing_period_job, False

        job = BalanceClosingJob.objects.create(
            comissao_id=comissao_id,
            requested_by_user_id=requested_by_user_id,
            session_id=session_id or 0,
            year=comissao.ano,
            month=comissao.mes,
            sequence=comissao.sequence,
            message='Fechamento solicitado; aguardando a finalização do serviço.',
        )
        return job, True
