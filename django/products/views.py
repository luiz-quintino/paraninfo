import calendar
import json
import os
import unicodedata
from html import escape
from datetime import date, datetime
from email.mime.image import MIMEImage
from email.utils import formataddr, parseaddr
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render

from users.models import tbAssociados

from .models import lstParcelas, tbCompra, tbMediaFiles, tbParcelamento, tbPlanoPagamentoProduto, tbProduto
from config.menus import MENU_VOLTAR, MENU_PRODUTOS_INCLUIR
from utils import save_log, is_admin, is_app_admin, user_role

def get_associado(request):
	return get_object_or_404(tbAssociados, uuid=request.user.last_name)


def _attach_product_images(products):
	products = list(products)

	media_ids = {product.img_id for product in products if product.img_id}
	media_files = {
		media.id: media
		for media in tbMediaFiles.objects.filter(id__in=media_ids)
	}

	for product in products:
		media = media_files.get(product.img_id)
		
		product.image_url = (
			f"{media.folder.rstrip('/')}/{media.new_file_name}"
			if media and media.folder else '/static/empty.png'
		)
	return products


def _payment_options_by_product(products):
	# Atualiza a lista de planos de pagamentos
	products_by_id = {product.id: product for product in products}
	links = list(
		tbPlanoPagamentoProduto.objects.filter(produto_id__in=products_by_id).order_by('id')
	)

	plan_codes = {link.plano_pagamento_id for link in links}
	payment_type_ids = {link.parcelas_id for link in links}
	payment_types = {
		payment_type.id: payment_type
		for payment_type in lstParcelas.objects.filter(id__in=payment_type_ids)
	}
	schedules = {}
	for installment in tbParcelamento.objects.filter(
		plano_pagamento__in=plan_codes
	).order_by('plano_pagamento', 'parcela_numero', 'id'):
		schedules.setdefault(installment.plano_pagamento, []).append(installment)

	options = {}
	for link in links:
		payment_type = payment_types.get(link.parcelas_id)
		source_installments = schedules.get(link.plano_pagamento_id, [])
		product = products_by_id.get(link.produto_id)
		if payment_type and source_installments and product:
			installments_by_quantity = {}
			try:
				for quantity in range(1, 6):
					installments_by_quantity[str(quantity)] = [
						{
							'number': item['number'],
							'value': str(item['value']),
							'due_date': item['due_date'].isoformat(),
						}
						for item in _build_purchase_schedule(
							product,
							link.parcelas_id,
							source_installments,
							quantity,
						)
					]
			except ValueError:
				continue
			options.setdefault(link.produto_id, []).append({
				'id': link.id,
				'payment_type': payment_type.tipo,
				'installments': installments_by_quantity['1'],
				'installments_by_quantity': installments_by_quantity,
			})
	return options


def product_my_list_context(request, associado):
	is_admin_ = is_admin(request)

	# Lista somente produtos do associado específico
	purchases = list(
		tbCompra.objects.filter(associado=associado)
		.select_related('produto', 'aprovador_associado')
		.order_by('produto')
	)
	products = _attach_product_images(
		purchase.produto for purchase in purchases if purchase.produto
	)
	products_by_id = {product.id: product for product in products}
	plan_codes = {purchase.plano_pagamento for purchase in purchases if purchase.plano_pagamento}
	installments_by_plan = {}
	for installment in tbParcelamento.objects.filter(
		plano_pagamento__in=plan_codes
	).order_by('plano_pagamento', 'parcela_numero', 'id'):
		installments_by_plan.setdefault(installment.plano_pagamento, []).append(installment)

	for purchase in purchases:
		purchase.product_image_url = getattr(products_by_id.get(purchase.produto_id), 'image_url', None)
		purchase.payment_installments = installments_by_plan.get(purchase.plano_pagamento, [])
	
	return {
		'products': products,
		'purchases': purchases,
		'is_admin': is_admin_,
	}

def product_list_context(request, associado):
	is_admin_ = user_role(request) in ['presidente', 'vice-presidente', 'secretario'] or is_app_admin(request)
	purchase_status = -1
	purchased_product_ids = []
	# lista todos os produtos se o usuário for admin, caso contrário, lista apenas produtos ativos
	products = tbProduto.objects.all() if is_admin_ else tbProduto.objects.filter(ativo=1)
	products = _attach_product_images(products.order_by('produto', 'id'))

	# lista de compras do associado, se houver
	purchases = tbCompra.objects.filter(associado=associado)

	purchased_product_ids = set(purchases.values_list('produto_id', flat=True)) 

	pending_count = tbCompra.objects.filter(status=tbCompra.STATUS_PENDENTE).count() if is_admin_ else 0 

	return {
		'products': products,
		'payment_options_by_product': _payment_options_by_product(products),
		'purchased_product_ids': purchased_product_ids,
		'is_admin': is_admin_,
		'pending_count': pending_count
	}


@login_required
def product_list(request, UUID=None):
	message = {'type': 'info', 'text': '', 'title': 'Lista de Produtos', 'function': ''}
	menu_options = [MENU_VOLTAR]

	if user_role(request) in ['presidente', 'vice-presidente', 'secretario'] or is_app_admin(request):
		menu_options.append(MENU_PRODUTOS_INCLUIR)

	if UUID:
		# Lista somente produtos do associado específico
		associado = get_object_or_404(tbAssociados, uuid=UUID)
	else:
		associado = get_associado(request)

	# The selected product plan is validated and copied to a purchase-specific plan code.
	if request.method == 'POST' and request.POST.get('action') in ('buy', 'buy_more'):
		product = get_object_or_404(tbProduto, pk=request.POST.get('product_id'))
		if not product.ativo and not is_admin(request):
			messages.error(request, 'Este produto não está disponível para compra.')
		else:
			try:
				quantity = int(request.POST.get('quantidade', '1'))
				if not 1 <= quantity <= 5:
					raise ValueError('A quantidade deve estar entre 1 e 5.')

				option_id = int(request.POST.get('payment_option_id', ''))
				plan_link = tbPlanoPagamentoProduto.objects.filter(
					pk=option_id,
					produto_id=product.id,
				).first()
				if plan_link is None:
					raise ValueError('A opção de pagamento selecionada não pertence a este produto.')
				source_installments = list(tbParcelamento.objects.filter(
					plano_pagamento=plan_link.plano_pagamento_id
				).order_by('parcela_numero', 'id'))
				if not source_installments:
					raise ValueError('O plano selecionado não possui parcelas cadastradas.')
				purchase_schedule = _build_purchase_schedule(
					product,
					plan_link.parcelas_id,		# a vista, parcelado, entrada + parcelas
					source_installments,
					quantity,
				)

				with transaction.atomic():
					# Lock existing plan rows while reserving a new code for this purchase.
					list(tbParcelamento.objects.select_for_update().order_by('id'))
					last_schedule_number = tbParcelamento.objects.aggregate(
						last_number=Max('plano_pagamento')
					)['last_number'] or 0
					last_link_number = tbPlanoPagamentoProduto.objects.aggregate(
						last_number=Max('plano_pagamento_id')
					)['last_number'] or 0
					last_purchase_number = tbCompra.objects.aggregate(
						last_number=Max('plano_pagamento')
					)['last_number'] or 0
					new_plan_number = max(
						last_schedule_number,
						last_link_number,
						last_purchase_number,
					) + 1

					for installment in purchase_schedule:
						tbParcelamento.objects.create(
							plano_pagamento=new_plan_number,
							parcela_numero=installment['number'],
							valor=installment['value'],
							dt_vencimento=installment['due_date'],
							origem=2,
						)

					tbCompra.objects.create(
						produto=product,
						associado=associado,
						dt_compra=date.today(),
						valor_original=product.valor_original * quantity,
						valor_acrescimo=(product.vr_acrescimo or Decimal('0.00')) * quantity,
						valor_desconto=(product.vr_desconto or Decimal('0.00')) * quantity,
						valor_total=product.valor_total * quantity,
						status=tbCompra.STATUS_PENDENTE,
						plano_pagamento=new_plan_number,
						quantidade=quantity,
					)

				messages.success(request, 'Compra registrada com sucesso. Aprovação pendente.')
				sending_email = purchase_mail (purchase_schedule, product, quantity, request, associado)
				# payment_text = ''.join([' '.join(['   ',f'{str(compra['number']):2}:',str(compra['due_date'].strftime("%d/%m/%Y")), f'R${compra["value"]:>8.2f}', '\n']) for compra in purchase_schedule])
				# email_error = False
				# subject = f'Compra - {product.produto}'
				# success_message = (
				# 	f'Compra realizada\n\n'
				# 	f'Situação: Pendente de aprovação.\n\n'
				# 	f'Produto: {product.produto}\n'
				# 	f'Quantidade: {quantity}\n'
				# 	f'{product.descricao}\n\n'
				# 	f'Valor total: R${product.valor_total}\n'
				# 	f'Plano de pagamento:\n{payment_text}\n\n'
				# 	f'Atenciosamente,\n{request.comissao_title}'
				# )
				# try:
				# 	from_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
				# 	email = EmailMultiAlternatives(
				# 		subject=subject,
				# 		body=success_message,
				# 		from_email=formataddr(('Paraninfo', from_address)),
				# 		to=[associado.email],
				# 	)
				# 	media = tbMediaFiles.objects.filter(id=product.img_id).first()
				# 	image_html = ''
				# 	if media:
				# 		media_folder = media.folder.removeprefix('/media/').strip('/')
				# 		image_path = (Path(settings.MEDIA_ROOT) / media_folder / media.new_file_name).resolve()
				# 		if image_path.is_file():
				# 			image_html = '<p><img src="cid:product-image" alt="Imagem do produto" style="max-width:500px;height:auto;"></p>'
				# 			image = MIMEImage(image_path.read_bytes())
				# 			image.add_header('Content-ID', '<product-image>')
				# 			image.add_header('Content-Disposition', 'inline', filename=media.new_file_name)
				# 			email.attach(image)
				# 	html_message = (
				# 		f'<h2>{escape(subject)}</h2>'
				# 		f'{image_html}'
				# 		f'<p><strong>Situação:</strong> Pendente de aprovação.</p>'
				# 		f'<p><strong>Produto:</strong> {escape(product.produto)}<br>'
				# 		f'<strong>Quantidade:</strong> {quantity}<br>{escape(product.descricao)}</p>'
				# 		f'<p><strong>Valor total:</strong> R$ {product.valor_total}</p>'
				# 		f'<p><strong>Plano de pagamento:</strong><br>{escape(payment_text).replace(chr(10), "<br>")}</p>'
				# 		f'<p>Atenciosamente,<br>{escape(request.comissao_title or "Paraninfo")}</p>'
				# 	)
				# 	email.attach_alternative(html_message, 'text/html')
				# 	email.send(fail_silently=False)
				# except Exception:
				# 	email_error = True

			except (ValueError, TypeError) as error:
				messages.error(request, f'Selecione um plano de pagamento válido. {error}')

		return redirect('products:product_list')

	context = product_list_context(request, associado)
	context['menu_options'] = menu_options
	context['message'] = message

	if UUID:
		context['message']['title'] = f'Lista de Produtos ({associado.nome_responsavel})'
			
	return render(request, 'products/product_list.html', context)


def _payment_kind(payment_type):
	label = unicodedata.normalize('NFKD', payment_type.tipo or '')
	label = ''.join(character for character in label if not unicodedata.combining(character)).lower()
	if 'entrada' in label:
		return 'entry'
	if 'vista' in label:
		return 'cash'
	if 'parcel' in label:
		return 'installments'
	return {1: 'cash', 2: 'installments', 3: 'entry'}.get(payment_type.id)


def _next_due_date(month_offset, due_day, today=None):
	today = today or date.today()
	month_index = today.year * 12 + today.month - 1 + month_offset
	year = month_index // 12
	month = month_index % 12 + 1
	due_date = date(year, month, min(due_day, calendar.monthrange(year, month)[1]))
	if month_offset == 0 and due_date < today:
		return _next_due_date(1, due_day, today)
	return due_date


def _monthly_due_dates(count, due_day, today=None):
	if count < 1:
		return []
	first_due_date = _next_due_date(0, due_day, today)
	first_month_index = first_due_date.year * 12 + first_due_date.month - 1
	due_dates = []
	for month_offset in range(count):
		month_index = first_month_index + month_offset
		year = month_index // 12
		month = month_index % 12 + 1
		due_dates.append(date(year, month, min(due_day, calendar.monthrange(year, month)[1])))
	return due_dates


def _product_due_dates(count, start_date, due_day):
	if count < 1:
		return []
	due_dates = []
	first_month_offset = int(due_day < start_date.day)
	for month_offset in range(count):
		month_index = start_date.year * 12 + start_date.month - 1 + first_month_offset + month_offset
		year = month_index // 12
		month = month_index % 12 + 1
		due_dates.append(date(year, month, min(due_day, calendar.monthrange(year, month)[1])))
	return due_dates


def _build_purchase_schedule(product, payment_type_id, source_installments, quantity, today=None):
	# Ajusta as datas dos plano de pagamento de acordo com a opção em ajustar
	today = today or date.today()
	total_value = product.valor_total * quantity
	due_day = product.dia_vencimento

	if payment_type_id == 1:	# a vista, parcelado, entrada + parcelas
		values = [total_value]
		due_dates = _monthly_due_dates(1, due_day, today)
	elif payment_type_id in (2, 3):
		# ajustar atrasadas: 0 não ajustar (vencimento a partir do próximo mês), 1 ajustar (calcular vencidas e distribuir valores a vencer), 2 manter datas originais
		
		# não ajustar
		if product.ajustar_atrasadas == 0:	# Distribuir em parcelas futuras
			installment_count = max(1, len(source_installments))
			values = _split_amount(total_value, installment_count)
			due_dates = _monthly_due_dates(installment_count, due_day, today)
		
		#  1 ajustar
		elif product.ajustar_atrasadas == 1:	# Acumular parcelas vencidas
			overdue = [item for item in source_installments if item.dt_vencimento <= today]
			upcoming = [item for item in source_installments if item.dt_vencimento > today]
			if payment_type_id == 2:
				if not upcoming:
					raise ValueError('Não há parcelas a vencer para recalcular este plano.')
				installment_total = sum(
					(item.valor for item in source_installments), Decimal('0.00')
				) * quantity
				values = _split_amount(installment_total, len(upcoming))
				due_dates = _monthly_due_dates(len(upcoming), due_day, today)
			else:						# Manter com datas vencidas
				if not upcoming:
					raise ValueError('Não há parcelas a vencer para recalcular este plano.')
				first_value = (
					sum((item.valor for item in overdue), Decimal('0.00'))
					+ upcoming[0].valor
				) * quantity
				values = [first_value, *(item.valor * quantity for item in upcoming[1:])]
				due_dates = _monthly_due_dates(len(upcoming), due_day, today)
		
		else: 	# manter datas originais
			installment_count = max(1, len(source_installments))
			values = _split_amount(total_value, installment_count)
			due_dates = [item.dt_vencimento for item in source_installments]

	else:
		return [
			{
				'number': index,
				'value': item.valor * quantity,
				'due_date': item.dt_vencimento,
			}
			for index, item in enumerate(source_installments, start=1)
		]

	return [
		{'number': index, 'value': value, 'due_date': due_date}
		for index, (value, due_date) in enumerate(zip(values, due_dates), start=1)
	]


def _split_amount(total, count):
	"""Distribute cents evenly so the installment amounts add up exactly."""
	total_cents = int((total * 100).quantize(Decimal('1')))
	base_amount, extra_cents = divmod(total_cents, count)
	return [
		(Decimal(base_amount + (index < extra_cents)) / 100).quantize(Decimal('0.01'))
		for index in range(count)
	]


def _validate_product_image(uploaded_image):
	if uploaded_image.size > 10 * 1024 * 1024:
		raise ValueError('A imagem deve ter no máximo 10 MB.')

	extension = Path(uploaded_image.name.replace('\\', '/')).suffix.lower()
	image_signatures = {
		'.jpg': lambda content: content.startswith(b'\xff\xd8\xff'),
		'.jpeg': lambda content: content.startswith(b'\xff\xd8\xff'),
		'.png': lambda content: content.startswith(b'\x89PNG\r\n\x1a\n'),
		'.gif': lambda content: content.startswith((b'GIF87a', b'GIF89a')),
		'.webp': lambda content: content.startswith(b'RIFF') and content[8:12] == b'WEBP',
	}
	if extension not in image_signatures:
		raise ValueError('Formato de imagem inválido. Use JPG, PNG, GIF ou WEBP.')

	header = uploaded_image.read(16)
	uploaded_image.seek(0)
	if not image_signatures[extension](header):
		raise ValueError('O conteúdo enviado não corresponde a um arquivo de imagem válido.')

	return extension


@login_required
def product_new(request):
	message = {'type': 'info', 'text': '', 'title': 'Incluir produto', 'function': ''}
	menu_options = [MENU_VOLTAR]
	payment_types = list(lstParcelas.objects.all().order_by('id'))
	payment_options = [
		{'id': option.id, 'tipo': option.tipo, 'kind': _payment_kind(option)}
		for option in payment_types
	]

	form_data = request.POST if request.method == 'POST' else {}
	saved_image_path = None

	if request.method == 'POST':
		if request.POST.get('action') == 'cancel':
			return redirect('products:product_list')

		try:
			name = request.POST.get('produto', '').strip()
			description = request.POST.get('descricao', '').strip()
			original_value = Decimal(request.POST.get('valor_original', '').replace(',', '.'))
			increase = Decimal(request.POST.get('acrescimo', '0').replace(',', '.') or '0')
			discount = Decimal(request.POST.get('desconto', '0').replace(',', '.') or '0')
			start_date = date.fromisoformat(request.POST.get('dt_inicio', ''))
			forecast_date_value = request.POST.get('dt_previsao') or None
			due_day = int(request.POST.get('dia_vencimento', '7'))
			forecast_date = date.fromisoformat(forecast_date_value) if forecast_date_value else None
			selected_plans = json.loads(request.POST.get('payment_plans', '[]'))

			# print("***", selected_plans)

			if not name or not description:
				raise ValueError('Informe o nome e a descrição do produto.')
			if any(not value.is_finite() for value in (original_value, increase, discount)):
				raise ValueError('Informe valores monetários válidos.')
			if original_value < 0 or increase < 0 or discount < 0:
				raise ValueError('Os valores não podem ser negativos.')
			if not 1 <= due_day <= 31:
				raise ValueError('O dia do vencimento deve estar entre 1 e 31.')
			total_value = original_value + increase - discount
			if total_value < 0:
				raise ValueError('O desconto não pode superar o valor total do produto.')
			if not isinstance(selected_plans, list) or not selected_plans:
				raise ValueError('Adicione pelo menos um plano de pagamento.')

			# print(payment_options)

			payment_types_by_id = {option.id: option for option in payment_types}
			validated_plans = []
			for selected_plan in selected_plans:
				if not isinstance(selected_plan, dict):
					raise ValueError('A seleção de planos de pagamento é inválida.')
				payment_type_id = selected_plan.get('payment_type_id')
				if isinstance(payment_type_id, bool):
					raise ValueError('Selecione um tipo de pagamento válido.')
				payment_type = payment_types_by_id.get(int(payment_type_id))
				if payment_type is None:
					raise ValueError('Selecione um tipo de pagamento válido.')
				kind = _payment_kind(payment_type)
				
				if kind not in ('cash', 'installments', 'entry'):
					raise ValueError('O tipo de pagamento selecionado não é reconhecido.')

				if kind == 'cash':
					installment_count = 1
				else:
					installment_count = int(selected_plan.get('installments', 0))
					if not 1 <= installment_count <= 120:
						raise ValueError('Informe entre 1 e 120 parcelas para o plano escolhido.')
					if kind == 'entry':
						installment_count += 1

				provided_schedule = selected_plan.get('schedule')
				if provided_schedule is None:
					installment_values = _split_amount(total_value, installment_count)
					schedule = [
						{'value': value, 'due_date': due_date}
						for value, due_date in zip(
							installment_values,
							_product_due_dates(installment_count, start_date, due_day),
						)
					]
				else:
					if not isinstance(provided_schedule, list) or not 1 <= len(provided_schedule) <= 121:
						raise ValueError('O plano deve conter entre 1 e 121 parcelas.')
					
					schedule = []
					for installment in provided_schedule:
						if not isinstance(installment, dict):
							raise ValueError('Os detalhes de uma parcela são inválidos.')
						installment_value = Decimal(str(installment.get('value', '')).replace(',', '.'))
						if not installment_value.is_finite() or installment_value < 0:
							raise ValueError('Informe valores válidos e não negativos para cada parcela.')
						if installment_value != installment_value.quantize(Decimal('0.01')) or installment_value >= Decimal('100000000'):
							raise ValueError('O valor de cada parcela deve ter até duas casas decimais e no máximo 10 dígitos.')
						installment_date = date.fromisoformat(installment.get('due_date', ''))
						schedule.append({'value': installment_value, 'due_date': installment_date})
					
					installment_count = len(schedule)
				validated_plans.append((payment_type, installment_count, schedule))


			# print(validated_plans)
			associated = tbAssociados.objects.filter(
				uuid=request.user.last_name
			).first()

			if associated is None:
				raise ValueError('O usuário administrador precisa estar vinculado a um associado para cadastrar produtos.')
			associated_id = associated.id

			commission_id = getattr(request, 'comissao', None) or associated.comissao
			if not commission_id:
				raise ValueError('Não foi possível identificar a comissão da sessão para salvar a imagem.')
			uploaded_image = request.FILES.get('imagem')
			image_extension = _validate_product_image(uploaded_image) if uploaded_image else None
			
			# cria log
			log_id = save_log(request,
				description='tbProduto',
				evento_log_id=14  # log: Adicionado novo produto 
			)

			product = tbProduto(
				produto=name,
				descricao=description,
				valor_original=original_value,
				dt_inicio=start_date,
				dt_previsao=forecast_date,
				associado_id=associated_id,
				img_id=None,
				vr_desconto=discount,
				vr_acrescimo=increase,
				dia_vencimento=due_day,
				ajustar_atrasadas=int(request.POST.get('adjust')),
				ativo=int(request.POST.get('ativo')),
				log_id=log_id
			)

			with transaction.atomic():
				# Reserve the first payment-group number before inserting the product;
				# tbProduto.plano_pagamento_id is NOT NULL in the database.
				list(lstParcelas.objects.select_for_update().order_by('id'))
				last_schedule_number = tbParcelamento.objects.aggregate(
					last_number=Max('plano_pagamento')
				)['last_number'] or 0
				last_link_number = tbPlanoPagamentoProduto.objects.aggregate(
					last_number=Max('plano_pagamento_id')
				)['last_number'] or 0
				next_plan_number = max(last_schedule_number, last_link_number) + 1
				product.plano_pagamento_id = next_plan_number
				product.save(force_insert=True)
				
				if uploaded_image:
					folder = f'{commission_id}/img'
					absolute_folder = Path(settings.MEDIA_ROOT) / str(commission_id) / 'img'
					absolute_folder.mkdir(parents=True, exist_ok=True)
					original_name = os.path.basename(uploaded_image.name.replace('\\', '/'))[:255]
					timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
					new_file_name = f'{timestamp}{image_extension}'
					saved_image_path = absolute_folder / new_file_name
					collision = 1
					while saved_image_path.exists():
						new_file_name = f'{timestamp}-{collision}{image_extension}'
						saved_image_path = absolute_folder / new_file_name
						collision += 1
					with saved_image_path.open('wb') as destination:
						for chunk in uploaded_image.chunks():
							destination.write(chunk)
					media = tbMediaFiles.objects.create(
						original_file_name=original_name,
						new_file_name=new_file_name,
						folder=f'/media/{folder}',
					)
					product.img_id = media.id
					product.save(force_update=True)

				for payment_type, installment_count, schedule in validated_plans:
					tbPlanoPagamentoProduto.objects.create(
						produto_id=product.id,
						plano_pagamento_id=next_plan_number,
						parcelas_id=payment_type.id,
					)
					
					for installment_number, installment in enumerate(schedule, start=1):
						tbParcelamento.objects.create(
							plano_pagamento=next_plan_number,
							parcela_numero=installment_number,
							valor=installment['value'],
							dt_vencimento=installment['due_date'],
							origem=1,
						)
					next_plan_number += 1
					
		except (InvalidOperation, TypeError, json.JSONDecodeError):
			if saved_image_path:
				saved_image_path.unlink(missing_ok=True)
			messages.error(request, 'Não foi possível salvar. Confira os dados e os planos de pagamento informados.')
		except IntegrityError as error:
			if saved_image_path:
				saved_image_path.unlink(missing_ok=True)
			messages.error(
				request,
				f'Falha de integridade ao gravar produto/plano: {error}',
			)
		except ValueError as error:
			if saved_image_path:
				saved_image_path.unlink(missing_ok=True)
			messages.error(request, str(error))
		except OSError:
			if saved_image_path:
				saved_image_path.unlink(missing_ok=True)
			messages.error(request, 'Não foi possível salvar o arquivo da imagem no diretório de mídia.')
		else:
			messages.success(request, 'Produto e planos de pagamento cadastrados com sucesso.')
			return redirect('products:product_list')

	context = {
		'menu_options': menu_options,
		'message': message,
		'payment_options': payment_options,
		'form_data': form_data,
	}
	return render(request, 'products/product_new.html', context)


@login_required
def product_my_list(request, UUID=None):
	message = {'type': 'info', 'text': '', 'title': 'Meu produtos adquiridos', 'function': ''}
	menu_options = [MENU_VOLTAR]

	is_admin_ = is_admin(request)

	# Se é admin, redireciona para product_list, pois o admin pode ver todos os produtos
	if not UUID:
		# erro if no user is passed
		messages.error(request, 'Associado não encontrado.')
		return redirect('products:product_list')

	associado = get_object_or_404(tbAssociados, uuid=UUID)
	context = product_my_list_context(request, associado)
	context['menu_options'] = menu_options
	context['message'] = message
	context['message']['title'] = f'Meu produtos adquiridos ({associado.nome_responsavel})'
	return render(request, 'products/product_my_list.html', context)


@login_required
def product_edit(request, product_id):

	message = {'type': 'info', 'text': '', 'title': 'Editar Produto', 'function': ''}
	menu_options = [MENU_VOLTAR]

	product = get_object_or_404(tbProduto, pk=product_id)
	payment_types = list(lstParcelas.objects.all().order_by('id'))
	payment_options = [
		{'id': option.id, 'tipo': option.tipo, 'kind': _payment_kind(option)}
		for option in payment_types
	]

	product_image = _attach_product_images([product])[0].image_url
	form_data = request.POST if request.method == 'POST' else {}

	initial_plans = []
	links = list(tbPlanoPagamentoProduto.objects.filter(produto_id=product.id).order_by('id'))
	payment_types_by_id = {option.id: option for option in payment_types}
	
	for link in links:
		plan_type = payment_types_by_id.get(link.parcelas_id)
		if not plan_type:
			continue
		schedule = list(tbParcelamento.objects.filter(
			plano_pagamento=link.plano_pagamento_id
		).order_by('parcela_numero', 'id'))
		if schedule:
			initial_plans.append({
				'payment_type_id': plan_type.id,
				'installments': len(schedule),
				'schedule_edited': True,
				'schedule': [
					{'value': str(item.valor), 'due_date': item.dt_vencimento.isoformat()}
					for item in schedule
				],
			})
	initial_plans_json = json.dumps(initial_plans)

	if request.method == 'POST':
		if request.POST.get('action') == 'cancel':
			messages.info(request, 'Edição cancelada.')
			return redirect('products:product_list')

		saved_image_path = None
		try:
			product_name = request.POST.get('produto', '').strip()
			description = request.POST.get('descricao', '').strip()
			original_value = Decimal(request.POST.get('valor_original', '').replace(',', '.'))
			increase = Decimal(request.POST.get('acrescimo', '0').replace(',', '.') or '0')
			discount = Decimal(request.POST.get('desconto', '0').replace(',', '.') or '0')
			start_date = date.fromisoformat(request.POST.get('dt_inicio', ''))
			forecast_date = date.fromisoformat(request.POST['dt_previsao']) if request.POST.get('dt_previsao') else None
			due_day = int(request.POST.get('dia_vencimento', '7'))
			selected_plans = json.loads(request.POST.get('payment_plans', '[]'))
			if not product_name or not description:
				raise ValueError('Informe o nome e a descrição do produto.')
			if any(not amount.is_finite() or amount < 0 for amount in (original_value, increase, discount)):
				raise ValueError('Informe valores monetários válidos e não negativos.')
			if original_value + increase - discount < 0:
				raise ValueError('O desconto não pode superar o valor total do produto.')
			if not 1 <= due_day <= 31:
				raise ValueError('O dia do vencimento deve estar entre 1 e 31.')
			if not isinstance(selected_plans, list) or not selected_plans:
				raise ValueError('Adicione pelo menos um plano de pagamento.')

			validated_plans = []
			for selected_plan in selected_plans:
				if not isinstance(selected_plan, dict):
					raise ValueError('A seleção de planos de pagamento é inválida.')
				payment_type_id = int(selected_plan.get('payment_type_id'))
				payment_type = payment_types_by_id.get(payment_type_id)
				if payment_type is None or _payment_kind(payment_type) not in ('cash', 'installments', 'entry'):
					raise ValueError('Selecione um tipo de pagamento válido.')
				schedule_data = selected_plan.get('schedule')
				if not isinstance(schedule_data, list) or not 1 <= len(schedule_data) <= 121:
					raise ValueError('Cada plano deve conter entre 1 e 121 parcelas.')
				schedule = []
				for installment in schedule_data:
					if not isinstance(installment, dict):
						raise ValueError('Os dados de uma parcela são inválidos.')
					value = Decimal(str(installment.get('value', '')).replace(',', '.'))
					if not value.is_finite() or value < 0 or value != value.quantize(Decimal('0.01')) or value >= Decimal('100000000'):
						raise ValueError('Informe valores válidos com até duas casas decimais para cada parcela.')
					schedule.append({
						'value': value,
						'due_date': date.fromisoformat(installment.get('due_date', '')),
					})
				validated_plans.append((payment_type, schedule))

			uploaded_image = request.FILES.get('imagem')
			image_extension = _validate_product_image(uploaded_image) if uploaded_image else None
			associated = tbAssociados.objects.filter(id=product.associado_id).first()
			commission_id = getattr(request, 'comissao', None) or (associated.comissao if associated else None)
			if uploaded_image and not commission_id:
				raise ValueError('Não foi possível identificar a comissão para salvar a imagem.')

			with transaction.atomic():
				product.produto = product_name
				product.descricao = description
				product.valor_original = original_value
				product.vr_acrescimo = increase
				product.vr_desconto = discount
				product.dt_inicio = start_date
				product.dt_previsao = forecast_date
				product.dia_vencimento = due_day
				product.ativo = int(request.POST.get('ativo'))
				product.ajustar_atrasadas = int(request.POST.get('adjust'))
				product.parcelas = max(len(schedule) for _, schedule in validated_plans)

				if uploaded_image:
					folder = f'{commission_id}/img'
					absolute_folder = Path(settings.MEDIA_ROOT) / str(commission_id) / 'img'
					absolute_folder.mkdir(parents=True, exist_ok=True)
					original_name = os.path.basename(uploaded_image.name.replace('\\', '/'))[:255]
					timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
					new_file_name = f'{timestamp}{image_extension}'
					saved_image_path = absolute_folder / new_file_name
					collision = 1
					while saved_image_path.exists():
						new_file_name = f'{timestamp}-{collision}{image_extension}'
						saved_image_path = absolute_folder / new_file_name
						collision += 1
					with saved_image_path.open('wb') as destination:
						for chunk in uploaded_image.chunks():
							destination.write(chunk)
					media = tbMediaFiles.objects.create(
						original_file_name=original_name,
						new_file_name=new_file_name,
						folder=f'/media/{folder}',
					)
					product.img_id = media.id

				list(tbParcelamento.objects.select_for_update().order_by('id'))
				existing_links = list(
					tbPlanoPagamentoProduto.objects.select_for_update()
					.filter(produto_id=product.id)
					.order_by('id')
				)
				existing_plan_codes = {link.plano_pagamento_id for link in existing_links}
				existing_rows_by_plan = {}
				for installment in tbParcelamento.objects.filter(
					plano_pagamento__in=existing_plan_codes
				).order_by('plano_pagamento', 'parcela_numero', 'id'):
					existing_rows_by_plan.setdefault(installment.plano_pagamento, []).append(installment)

				existing_by_schedule = {}
				for link in existing_links:
					rows = existing_rows_by_plan.get(link.plano_pagamento_id, [])
					key = tuple((row.valor, row.dt_vencimento) for row in rows)
					existing_by_schedule.setdefault(key, []).append(link)

				last_schedule_number = tbParcelamento.objects.aggregate(last_number=Max('plano_pagamento'))['last_number'] or 0
				last_link_number = tbPlanoPagamentoProduto.objects.aggregate(last_number=Max('plano_pagamento_id'))['last_number'] or 0
				last_purchase_number = tbCompra.objects.aggregate(last_number=Max('plano_pagamento'))['last_number'] or 0
				next_plan_number = max(last_schedule_number, last_link_number, last_purchase_number) + 1
				retained_link_ids = set()
				first_plan_number = None
				for payment_type, schedule in validated_plans:
					schedule_key = tuple((item['value'], item['due_date']) for item in schedule)
					matching_links = existing_by_schedule.get(schedule_key, [])
					if matching_links:
						link = matching_links.pop(0)
						plan_number = link.plano_pagamento_id
						retained_link_ids.add(link.id)
						if link.parcelas_id != payment_type.id:
							tbPlanoPagamentoProduto.objects.filter(id=link.id).update(
								parcelas_id=payment_type.id
							)
					else:
						plan_number = next_plan_number
						tbPlanoPagamentoProduto.objects.create(
							produto_id=product.id,
							plano_pagamento_id=plan_number,
							parcelas_id=payment_type.id,
						)
						for number, installment in enumerate(schedule, start=1):
							tbParcelamento.objects.create(
								plano_pagamento=plan_number,
								parcela_numero=number,
								valor=installment['value'],
								dt_vencimento=installment['due_date'],
								origem=1,
							)
						next_plan_number += 1
					if first_plan_number is None:
						first_plan_number = plan_number

				links_to_remove = [link.id for link in existing_links if link.id not in retained_link_ids]
				if links_to_remove:
					tbPlanoPagamentoProduto.objects.filter(id__in=links_to_remove).delete()
				product.plano_pagamento_id = first_plan_number

				product.save(force_update=True)
		except (InvalidOperation, TypeError, ValueError, json.JSONDecodeError) as error:
			if saved_image_path:
				saved_image_path.unlink(missing_ok=True)
			messages.error(request, str(error) or 'Confira os dados informados.')
		except (IntegrityError, OSError) as error:
			if saved_image_path:
				saved_image_path.unlink(missing_ok=True)
			messages.error(request, f'Não foi possível salvar o produto: {error}')
		else:
			messages.success(request, 'Produto editado com sucesso.')
			log_id = save_log(request,
							description='tbProduto',
							evento_log_id=18  # log: Edita produto
						)
			return redirect('products:product_list')

	context = {
		'menu_options': menu_options,
		'message': message,
		'product': product,
		'product_image': product_image,
		'payment_options': payment_options,
		'form_data': form_data,
		'initial_plans_json': initial_plans_json,
	}
	return render(request, 'products/product_edit.html', context)


@login_required
def product_approval(request):
	message = {'type': 'info', 'text': '', 'title': 'Compras pendentes de aprovação', 'function': ''}
	menu_options = [MENU_VOLTAR]

	associado = get_associado(request)

	if request.method == 'POST':
		if request.POST.get('action'):
			action, record_id = request.POST.get('action').split(', ')

		purchase = get_object_or_404(tbCompra, pk=record_id, status=tbCompra.STATUS_PENDENTE)
		
		if action not in ('approve', 'reject'):
			messages.error(request, 'Ação de aprovação inválida.')
		else:
			try:
				purchase.valor_desconto = Decimal(request.POST.get('valor_desconto', '0') or '0')
				purchase.valor_acrescimo = Decimal(request.POST.get('valor_acrescimo', '0') or '0')
				purchase.valor_total = purchase.valor_original + purchase.valor_acrescimo - purchase.valor_desconto
			except InvalidOperation:
				messages.error(request, 'Informe valores válidos para desconto e acréscimo.')
			else:
				delta = purchase.valor_acrescimo - purchase.valor_desconto 
				if action == 'approve' and delta != 0:
					if delta > 0:
						# adiciona o valor do acréscimo à 1ª parcela
						parcela = tbParcelamento.objects.filter(plano_pagamento = purchase.plano_pagamento).first()
						novo_valor = parcela.valor + delta
						parcela_id = parcela.id
						tbParcelamento.objects.filter(id=parcela_id).update(valor=novo_valor)
					
					else:
						# deduz o valor do desconto às próximas parcelas
						parcelas = tbParcelamento.objects.filter(plano_pagamento = purchase.plano_pagamento)
						delta = -delta
						for parcela in parcelas:
							parcela_id = parcela.id
							if parcela.valor >= delta:
								novo_valor = parcela.valor - delta
								delta = Decimal('0.0')
								tbParcelamento.objects.filter(id=parcela_id).update(valor=novo_valor)
								continue

							else:
								delta = delta - parcela.valor
								novo_valor = Decimal('0.0')
								tbParcelamento.objects.filter(id=parcela_id).update(valor=novo_valor)
						
						# após a dedução, sobrou valor devido
						if delta > 0:
							# TODO erro, sobrou valor
							pass

				purchase.status = tbCompra.STATUS_APROVADO if action == 'approve' else tbCompra.STATUS_REPROVADO
				purchase.dt_aprovacao = date.today()
				purchase.aprovador_associado_id = associado.id
				purchase.save(force_update=True)
				messages.success(request, 'Compra aprovada.' if action == 'approve' else 'Compra reprovada.')
				log_id = save_log(request,
								description='tbProduto',
								evento_log_id=19  # log: Compra aprovada 
							)

				compra_result = 'APROVADA' if action == 'approve' else 'REPROVADA'
				sending_email = purchase_approved_mail (purchase.produto, request, associado, compra_result)
				return redirect('products:product_approval')

	purchases = tbCompra.objects.filter(status=tbCompra.STATUS_PENDENTE).select_related('produto', 'associado')

	context = {
		'menu_options': menu_options,
		'message': message,
		'purchases': purchases,
	}
	return render(request, 'products/product_approval.html', context)

from django.shortcuts import render

def purchase_mail(purchase_schedule, product, quantity, request, associado) -> bool:
	payment_text = ''.join([' '.join(['   ',f'{str(compra['number']):2}:',str(compra['due_date'].strftime("%d/%m/%Y")), f'R${compra["value"]:>8.2f}', '\n']) for compra in purchase_schedule])
	email_error = False
	subject = f'Recebemos seu pedio para {product.produto}'
	success_message = (
		f'Compra realizada\n\n'
		f'Situação: Pendente de aprovação.\n\n'
		f'Produto: {product.produto}\n'
		f'Quantidade: {quantity}\n'
		f'{product.descricao}\n\n'
		f'Valor total: R${product.valor_total}\n'
		f'Plano de pagamento:\n{payment_text}\n\n'
		f'Atenciosamente,\n{request.comissao_title}'
	)
	try:
		from_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
		email = EmailMultiAlternatives(
			subject=subject,
			body=success_message,
			from_email=formataddr(('Paraninfo', from_address)),
			to=[associado.email],
		)
		media = tbMediaFiles.objects.filter(id=product.img_id).first()
		image_html = ''
		if media:
			media_folder = media.folder.removeprefix('/media/').strip('/')
			image_path = (Path(settings.MEDIA_ROOT) / media_folder / media.new_file_name).resolve()
			if image_path.is_file():
				image_html = '<p><img src="cid:product-image" alt="Imagem do produto" style="max-width:500px;height:auto;"></p>'
				image = MIMEImage(image_path.read_bytes())
				image.add_header('Content-ID', '<product-image>')
				image.add_header('Content-Disposition', 'inline', filename=media.new_file_name)
				email.attach(image)
		html_message = (
			f'<h2>{escape(subject)}</h2>'
			f'{image_html}'
			f'<p><strong>Situação:</strong> Pendente de aprovação.</p>'
			f'<p><strong>Produto:</strong> {escape(product.produto)}<br>'
			f'<strong>Quantidade:</strong> {quantity}<br>{escape(product.descricao)}</p>'
			f'<p><strong>Valor total:</strong> R$ {product.valor_total}</p>'
			f'<p><strong>Plano de pagamento:</strong><br>{escape(payment_text).replace(chr(10), "<br>")}</p>'
			f'<p>Atenciosamente,<br>{escape(request.comissao_title or "Paraninfo")}</p>'
		)
		email.attach_alternative(html_message, 'text/html')
		email.send(fail_silently=False)
	except Exception:
		email_error = True

	return email_error

def purchase_approved_mail(product, request, associado, result) -> bool:
	email_error = False
	subject = f'Resulta do seu pedido para {product.produto}'
	success_message = (
		f'Situação da Compra: {result}.\n\n'
		f'Produto: {product.produto}\n'
		f'{product.descricao}\n\n'
		f'Valor total: R${product.valor_total}\n'
		f'Atenciosamente,\n{request.comissao_title}'
	)
	
	try:
		from_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
		email = EmailMultiAlternatives(
			subject=subject,
			body=success_message,
			from_email=formataddr(('Paraninfo', from_address)),
			to=[associado.email],
		)
		media = tbMediaFiles.objects.filter(id=product.img_id).first()
		image_html = ''
		if media:
			media_folder = media.folder.removeprefix('/media/').strip('/')
			image_path = (Path(settings.MEDIA_ROOT) / media_folder / media.new_file_name).resolve()
			if image_path.is_file():
				image_html = '<p><img src="cid:product-image" alt="Imagem do produto" style="max-width:500px;height:auto;"></p>'
				image = MIMEImage(image_path.read_bytes())
				image.add_header('Content-ID', '<product-image>')
				image.add_header('Content-Disposition', 'inline', filename=media.new_file_name)
				email.attach(image)
		html_message = (
			f'<h2>{escape(subject)}</h2>'
			f'{image_html}'
			f'<p><strong>Situação da compra:</strong> {escape(result)}</p>'
			f'<p><strong>Produto:</strong> {escape(product.produto)}<br>'
			f'<strong>Quantidade:</strong> {escape(product.descricao)}</p>'
			f'<p><strong>Valor total:</strong> R$ {product.valor_total}</p>'
			f'<p>Atenciosamente,<br>{escape(request.comissao_title or "Paraninfo")}</p>'
		)
		email.attach_alternative(html_message, 'text/html')
		email.send(fail_silently=False)
	except Exception:
		email_error = True

	return email_error