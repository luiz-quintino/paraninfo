from django.db import models
from users.models import tbAssociados


class lstprodutoativo(models.Model):
	id = models.AutoField(primary_key=True)
	tipo = models.CharField(max_length=45)

	class Meta:
		db_table = 'lstprodutoativo'
		managed = False


class tbProduto(models.Model):
	id = models.AutoField(primary_key=True)
	produto = models.CharField(max_length=255)
	descricao = models.CharField(max_length=255)
	valor_original = models.DecimalField(max_digits=10, decimal_places=2)
	dt_inicio = models.DateField()
	dt_previsao = models.DateField(null=True, blank=True)
	associado_id = models.IntegerField()
	img_id = models.IntegerField(null=True, blank=True)
	vr_desconto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	vr_acrescimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	dia_vencimento = models.IntegerField()
	ajustar_atrasadas = models.IntegerField()
	log_id = models.IntegerField()

	# Relacionamentos
	ativo = models.ForeignKey(
		lstprodutoativo,
		on_delete=models.SET_NULL,
		db_column='lstprodutoativo_id',
		null=True,
		blank=True,
		related_name='ativo'
	)
	ativo = models.IntegerField()

	@property
	def valor_total(self):
		return self.valor_original + (self.vr_acrescimo or 0) - (self.vr_desconto or 0)

	class Meta:
		db_table = 'tbProduto'
		managed = False


class lstParcelas(models.Model):
	id = models.AutoField(primary_key=True)
	tipo = models.CharField(max_length=45)

	class Meta:
		db_table = 'lstparcelas'
		managed = False


class tbParcelamento(models.Model):
	id = models.AutoField(primary_key=True)
	plano_pagamento = models.IntegerField()
	parcela_numero = models.IntegerField()
	valor = models.DecimalField(max_digits=10, decimal_places=2)
	dt_vencimento = models.DateField()
	origem = models.IntegerField(null=True, blank=True)
	
	class Meta:
		db_table = 'tbparcelamentos'
		managed = False


class tbPlanoPagamentoProduto(models.Model):
	id = models.AutoField(primary_key=True)
	produto_id = models.IntegerField()
	plano_pagamento_id = models.IntegerField(null=True, blank=True)
	parcelas_id = models.IntegerField(null=True, blank=True)
	
	class Meta:
		db_table = 'tbplanopagamentoproduto'
		managed = False


class tbMediaFiles(models.Model):
	id = models.AutoField(primary_key=True)
	original_file_name = models.CharField(max_length=255)
	new_file_name = models.CharField(max_length=45)
	folder = models.CharField(max_length=45)

	class Meta:
		db_table = 'tbmedia_files'
		managed = False


class tbCompra(models.Model):
	STATUS_PENDENTE = 0
	STATUS_APROVADO = 1
	STATUS_REPROVADO = 2

	id = models.AutoField(primary_key=True)
	associado = models.ForeignKey(tbAssociados, db_column='associado_id', on_delete=models.DO_NOTHING,
								  related_name='compras_produtos')
	dt_compra = models.DateField()
	dt_aprovacao = models.DateField(null=True, blank=True)
	valor_original = models.DecimalField(max_digits=10, decimal_places=2)
	valor_acrescimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	valor_total = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.IntegerField(default=STATUS_PENDENTE)
	plano_pagamento = models.IntegerField(null=True, blank=True)
	quantidade=models.IntegerField(default=1)

	# Relacionamentos
	produto = models.ForeignKey(
		tbProduto,
		on_delete=models.SET_NULL,
		db_column='produto_id',
		null=True,
		blank=True,
		related_name='produto_compra'
	)


	aprovador_associado = models.ForeignKey(
		tbAssociados,
		db_column='aprovador_associado_id',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='aprovador'
	)

	class Meta:
		db_table = 'tbCompra'
		managed = False

