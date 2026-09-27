from datetime import date
from decimal import Decimal, InvalidOperation
from urllib import request

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from users.models import tbAssociados

from .models import tbCompra, tbProduto
from config.menus import MENU_VOLTAR, MENU_PRODUTOS_INCLUIR

def is_product_admin(user):
	return user.is_authenticated and user.groups.filter(
		name__in=['sys-admin', 'app-admin', 'master']
	).exists()


def get_associado(request):
	return get_object_or_404(tbAssociados, uuid=request.user.last_name)

def product_my_list_context(request, associado):
	is_admin = is_product_admin(request.user)

	# Lista somente produtos do associado específico
	purchases = tbCompra.objects.filter(associado=associado)
	
	return {
		'purchases': purchases.order_by('produto'),
		'is_admin': is_admin,
	}

def product_list_context(request, associado):
	is_admin = is_product_admin(request.user)
	purchase_status = -1
	purchased_product_ids = []
	# lista todos os produtos se o usuário for admin, caso contrário, lista apenas produtos ativos
	products = tbProduto.objects.all() if is_admin else tbProduto.objects.filter(ativo=True)

	# lista de compras do associado, se houver
	purchases = tbCompra.objects.filter(associado=associado)

	purchased_product_ids = set(purchases.values_list('produto_id', flat=True)) 

	pending_count = tbCompra.objects.filter(status=tbCompra.STATUS_PENDENTE).count() if is_admin else 0 
	
	return {
		'products': products.order_by('produto', 'id'),
		'purchased_product_ids': purchased_product_ids,
		'is_admin': is_admin,
		'pending_count': pending_count
	}


@login_required
def product_list(request, UUID=None):
	message = {'type': 'info', 'text': '', 'title': 'Lista de Produtos', 'function': ''}
	menu_options = [MENU_VOLTAR]

	if is_product_admin(request.user):
		menu_options.append(MENU_PRODUTOS_INCLUIR)

	if UUID:
		# Lista somente produtos do associado específico
		associado = get_object_or_404(tbAssociados, uuid=UUID)
	else:
		associado = get_associado(request)

	# request.POST.get('action') can be 'buy', 'cancel_purchase', or 'buy_more'
	if request.method == 'POST' and (request.POST.get('action') == 'buy' or request.POST.get('action') == 'buy_more'):
		product = get_object_or_404(tbProduto, pk=request.POST.get('product_id'))
		if not product.ativo and not is_product_admin(request.user):
			messages.error(request, 'Este produto não está disponível para compra.')
		else:
			tbCompra.objects.create(
				produto=product,
				associado=associado,
				dt_compra=date.today(),
				tipo_pagamento=0,
				valor_original=product.valor_total,
				valor_acrescimo=Decimal('0.00'),
				valor_desconto=Decimal('0.00'),
				valor_total=product.valor_total,
				status=tbCompra.STATUS_PENDENTE,
			)
			messages.success(request, 'Compra registrada com sucesso. Aprovação pendente.')
		return redirect('products:product_list')

	context = product_list_context(request, associado)
	context['menu_options'] = menu_options
	context['message'] = message
	if UUID:
		context['message']['title'] = f'Lista de Produtos ({associado.nome_responsavel})'
			
	return render(request, 'products/product_list.html', context)

@login_required
def product_my_list(request, UUID=None):
	message = {'type': 'info', 'text': '', 'title': 'Meu produtos adquiridos', 'function': ''}
	menu_options = [MENU_VOLTAR]

	is_admin = is_product_admin(request.user)

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
@user_passes_test(is_product_admin)
def product_edit(request, product_id):
	message = {'type': 'info', 'text': '', 'title': 'Editar Produto', 'function': ''}
	menu_options = [MENU_VOLTAR]

	product = get_object_or_404(tbProduto, pk=product_id)


	if request.method == 'POST':
		print(request.POST)
		
		if request.POST.get('action') == 'cancel':
			messages.info(request, 'Edição cancelada.')
			return redirect('products:product_list')

		try:
			product.produto = request.POST.get('produto', '').strip()
			product.descricao = request.POST.get('descricao', '').strip()
			product.valor_original = Decimal(request.POST.get('valor_original', ''))
			product.vr_acrescimo = Decimal(request.POST.get('acrescimo', '0') or '0')
			product.vr_desconto = Decimal(request.POST.get('desconto', '0') or '0')
			product.dt_inicio = request.POST.get('dt_inicio')
			product.dt_previsao = request.POST.get('dt_previsao') or None
			product.ativo = request.POST.get('ativo') == 'on'
			if not product.produto or not product.descricao:
				raise ValueError
			product.save(force_update=True)
		except (InvalidOperation, ValueError):
			messages.error(request, 'Preencha corretamente os campos obrigatórios.')
		else:
			messages.success(request, 'Produto editado com sucesso.')
			return redirect('products:product_list')

	context = {
			'menu_options': menu_options,
			'message': message,
			'product': product
		}
	return render(request, 'products/product_edit.html', context)


@login_required
@user_passes_test(is_product_admin)
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
				purchase.status = tbCompra.STATUS_APROVADO if action == 'approve' else tbCompra.STATUS_REPROVADO
				purchase.dt_aprovacao = date.today()
				purchase.aprovador_associado_id = associado.id
				purchase.save(force_update=True)
				messages.success(request, 'Compra aprovada.' if action == 'approve' else 'Compra reprovada.')
				return redirect('products:product_approval')

	purchases = tbCompra.objects.filter(status=tbCompra.STATUS_PENDENTE).select_related('produto', 'associado')

	context = {
		'menu_options': menu_options,
		'message': message,
		'purchases': purchases,
	}
	return render(request, 'products/product_approval.html', context)

from django.shortcuts import render

