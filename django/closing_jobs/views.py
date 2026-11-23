from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .models import BalanceClosingJob


@login_required
def job_status(request, job_id):
	job = get_object_or_404(
		BalanceClosingJob,
		id=job_id,
		comissao_id=getattr(request, 'comissao', None),
	)
	return JsonResponse({
		'id': job.id,
		'status': job.status,
		'status_display': job.get_status_display(),
		'message': job.message,
		'finished': job.finished_at is not None,
	})
