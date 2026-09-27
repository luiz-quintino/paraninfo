from django.db import models
from users.models import tbAssociados


class tbProduto(models.Model):
	id = models.AutoField(primary_key=True)
	produto = models.CharField(max_length=255)
	descricao = models.CharField(max_length=255)
	valor_original = models.DecimalField(max_digits=10, decimal_places=2)
	dt_inicio = models.DateField()
	dt_previsao = models.DateField(null=True, blank=True)
	ativo = models.BooleanField()
	associado_id = models.IntegerField()
	img_id = models.IntegerField(null=True, blank=True)
	vr_desconto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	vr_acrescimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	parcelas = models.IntegerField()
	planopagamentoproduto_id = models.IntegerField()
	ajustar_atrasadas = models.IntegerField()
	

	@property
	def valor_total(self):
		return self.valor_original + (self.vr_acrescimo or 0) - (self.vr_desconto or 0)

	class Meta:
		db_table = 'tbProduto'
		managed = False


class tbCompra(models.Model):
	STATUS_PENDENTE = 0
	STATUS_APROVADO = 1
	STATUS_REPROVADO = 2

	id = models.AutoField(primary_key=True)
	produto = models.ForeignKey(tbProduto, db_column='produto_id', on_delete=models.DO_NOTHING)
	associado = models.ForeignKey(tbAssociados, db_column='associado_id', on_delete=models.DO_NOTHING,
								  related_name='compras_produtos')
	dt_compra = models.DateField()
	dt_aprovacao = models.DateField(null=True, blank=True)
	aprovador_associado = models.ForeignKey(tbAssociados, db_column='aprovador_associado_id', on_delete=models.DO_NOTHING,
											related_name='aprovador', null=True, blank=True)
	tipo_pagamento = models.IntegerField()
	reajuste_id = models.IntegerField(null=True, blank=True)
	valor_original = models.DecimalField(max_digits=10, decimal_places=2)
	valor_acrescimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	valor_total = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.IntegerField(default=STATUS_PENDENTE)
	plano_pagamento_id = models.IntegerField()


	# Relacionamento com tbProduto
	produto = models.ForeignKey(
		tbProduto,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='produto_compra'
	)

	aprovador_associado = models.ForeignKey(
		tbAssociados,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='aprovador'
	)

	class Meta:
		db_table = 'tbCompra'
		managed = False

