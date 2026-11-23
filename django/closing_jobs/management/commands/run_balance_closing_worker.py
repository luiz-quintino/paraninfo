import signal
import time

from django.core.management.base import BaseCommand, CommandError

from closing_jobs.worker import claim_next_job, process_job


shutdown_requested = False


def request_shutdown(signum, frame):
    global shutdown_requested
    shutdown_requested = True


class Command(BaseCommand):
    help = 'Consome a fila de fechamentos mensais do balanço.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--poll-interval',
            type=float,
            default=3.0,
            help='Segundos entre consultas à fila quando não há tarefas (padrão: 3).',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Processa no máximo uma tarefa e encerra; útil para testes.',
        )

    def handle(self, *args, **options):
        poll_interval = options['poll_interval']
        if poll_interval <= 0:
            raise CommandError('--poll-interval deve ser maior que zero.')

        global shutdown_requested
        shutdown_requested = False
        signal.signal(signal.SIGINT, request_shutdown)
        signal.signal(signal.SIGTERM, request_shutdown)

        self.stdout.write(self.style.SUCCESS('Worker de fechamento iniciado.'))
        while not shutdown_requested:
            job_id = claim_next_job()
            if job_id is None:
                if options['once']:
                    return
                time.sleep(poll_interval)
                continue

            self.stdout.write(f'Processando tarefa de fechamento #{job_id}.')
            process_job(job_id)
            self.stdout.write(f'Tarefa #{job_id} processada; consulte o estado no sistema.')
            if options['once']:
                return

        self.stdout.write('Worker encerrado após concluir a tarefa em andamento.')
