from types import SimpleNamespace

from django.db import close_old_connections, transaction
from django.utils import timezone

from balance.services.balance_calc import month_enclosed
from paraninfo_admin.models import tbComissao
from transaction.models import tbExtrato

from .models import BalanceClosingJob


def claim_next_job():
    """Atomically claim the oldest pending job. Run a single worker initially."""
    with transaction.atomic():
        job = (
            BalanceClosingJob.objects.select_for_update()
            .filter(status=BalanceClosingJob.PENDING)
            .order_by('created_at', 'id')
            .first()
        )
        if job is None:
            return None

        job.status = BalanceClosingJob.RUNNING
        job.started_at = timezone.now()
        job.message = 'Fechamento iniciado.'
        job.save(update_fields=['status', 'started_at', 'message'])
        return job.id


def process_job(job_id):
    close_old_connections()
    job = BalanceClosingJob.objects.get(id=job_id, status=BalanceClosingJob.RUNNING)

    try:
        comissao_db = tbComissao.objects.get(id=job.comissao_id)
        if (comissao_db.ano, comissao_db.mes, comissao_db.sequence) != (
            job.year, job.month, job.sequence
        ):
            raise RuntimeError(
                'A comissão mudou desde a solicitação. O fechamento não foi executado; '
                'revise o estado antes de tentar novamente.'
            )

        comissao = {
            'sequence': job.sequence,
            'title': comissao_db.nome_comissao,
            'inscricao': comissao_db.inscricao,
            'cnpj': comissao_db.cnpj,
            'comissao_id': job.comissao_id,
            'year': job.year,
            'month': job.month,
        }
        extratos = tbExtrato.objects.filter(
            comissao_id=job.comissao_id,
            data__year=job.year,
            data__month=job.month,
            status=2,
        ).select_related('transacao').order_by('id')
        if not extratos.exists():
            raise RuntimeError('Não há movimentações com status 2 para fechar neste período.')

        execution_context = SimpleNamespace(
            user_id=job.requested_by_user_id,
            session={'user_data': {'sessao_id': job.session_id}},
            resolver_match=SimpleNamespace(url_name='fechar_balanco'),
        )
        errors = month_enclosed(execution_context, comissao, extratos)

        comissao_db.refresh_from_db()
        if comissao_db.sequence != job.sequence + 1:
            details = '; '.join(f'{stage}: {error}' for stage, error in (errors or {}).items())
            raise RuntimeError(details or 'O fechamento terminou sem avançar a sequência da comissão.')

        if errors:
            job.status = BalanceClosingJob.COMPLETED_WITH_WARNINGS
            job.message = 'O fechamento avançou, mas houve avisos: ' + '; '.join(
                f'{stage}: {error}' for stage, error in errors.items()
            )
        else:
            job.status = BalanceClosingJob.SUCCEEDED
            job.message = 'Fechamento concluído com sucesso.'
    except Exception as error:
        job.status = BalanceClosingJob.FAILED
        job.message = str(error)[:4000]
    finally:
        job.finished_at = timezone.now()
        job.save(update_fields=['status', 'message', 'finished_at'])
        close_old_connections()
