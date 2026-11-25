import logging
from types import SimpleNamespace

from django.db import close_old_connections, transaction
from django.utils import timezone

from balance.services.balance_calc import month_enclosed
from paraninfo_admin.models import tbComissao
from transaction.models import tbExtrato

from .models import BalanceClosingJob


logger = logging.getLogger(__name__)


def _update_job_message(job_id, message):
    """Persist progress without allowing a status write to interrupt accounting work."""
    try:
        BalanceClosingJob.objects.filter(
            id=job_id,
            status=BalanceClosingJob.RUNNING,
        ).update(message=str(message)[:4000])
    except Exception:
        logger.exception('Não foi possível atualizar a mensagem do fechamento #%s.', job_id)


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
    current_phase = 'iniciando o processamento'

    def report_progress(message):
        nonlocal current_phase
        current_phase = message
        _update_job_message(job_id, message)

    try:
        report_progress('Validando comissão e período do fechamento...')
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
        report_progress(
            f'Período validado. Preparando fechamento de {extratos.count()} movimentações...'
        )

        execution_context = SimpleNamespace(
            user_id=job.requested_by_user_id,
            session={'user_data': {'sessao_id': job.session_id}},
            resolver_match=SimpleNamespace(url_name='fechar_balanco'),
        )
        errors = month_enclosed(
            execution_context,
            comissao,
            extratos,
            progress_callback=report_progress,
        )

        report_progress('Conferindo atualização da sequência do fechamento...')
        comissao_db.refresh_from_db()
        if comissao_db.sequence != job.sequence + 1:
            details = '; '.join(
                f'{stage}: {type(error).__name__}: {error}'
                for stage, error in (errors or {}).items()
            )
            raise RuntimeError(details or 'O fechamento terminou sem avançar a sequência da comissão.')

        if errors:
            job.status = BalanceClosingJob.COMPLETED_WITH_WARNINGS
            job.message = 'O fechamento avançou, mas houve avisos: ' + '; '.join(
                f'{stage}: {type(error).__name__}: {error}'
                for stage, error in errors.items()
            )
        else:
            job.status = BalanceClosingJob.SUCCEEDED
            job.message = 'Fechamento concluído com sucesso.'
    except Exception as error:
        logger.exception('Falha no fechamento #%s durante %s.', job_id, current_phase)
        job.status = BalanceClosingJob.FAILED
        job.message = (
            f'Falha durante {current_phase}: {type(error).__name__}: {error}'
        )[:4000]
    finally:
        job.finished_at = timezone.now()
        job.save(update_fields=['status', 'message', 'finished_at'])
        close_old_connections()
