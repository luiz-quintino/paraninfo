from pathlib import Path, PurePosixPath

from django.conf import settings

from products.models import tbMediaFiles


def get_comprovante_details(extrato):
	if not extrato.comprovante:
		return {'name': '', 'url': ''}

	media = tbMediaFiles.objects.filter(id=extrato.comprovante).first()
	if not media:
		return {'name': '', 'url': ''}

	original_name = (media.original_file_name or '').replace('\\', '/')
	folder = (media.folder or '').replace('\\', '/').rstrip('/')
	if folder.startswith('media/'):
		file_url = f'/{folder}/{media.new_file_name}'
	elif folder.startswith('/media/'):
		file_url = f'{folder}/{media.new_file_name}'
	else:
		file_url = f"{settings.MEDIA_URL.rstrip('/')}/{folder.strip('/')}/{media.new_file_name}"

	return {
		'name': PurePosixPath(original_name).stem,
		'url': file_url,
	}


def get_media_file_path(media):
	"""Return a media path only when it stays inside MEDIA_ROOT."""
	folder = (media.folder or '').replace('\\', '/').strip('/')
	if folder.startswith('media/'):
		folder = folder[len('media/'):]

	media_root = Path(settings.MEDIA_ROOT).resolve()
	file_path = (media_root / folder / media.new_file_name).resolve()
	try:
		file_path.relative_to(media_root)
	except ValueError:
		return None
	return file_path