from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from .views import _build_purchase_schedule, _product_due_dates, _split_amount


class PurchaseScheduleTests(SimpleTestCase):
	TODAY = date(2026, 10, 2)

	def test_product_schedule_uses_due_day_from_start_month(self):
		self.assertEqual(
			_product_due_dates(3, date(2026, 4, 1), 7),
			[date(2026, 4, 7), date(2026, 5, 7), date(2026, 6, 7)],
		)

	def test_product_schedule_clamps_due_day_to_short_month(self):
		self.assertEqual(
			_product_due_dates(2, date(2026, 1, 31), 31),
			[date(2026, 1, 31), date(2026, 2, 28)],
		)

	def test_product_schedule_does_not_precede_start_date(self):
		self.assertEqual(
			_product_due_dates(2, date(2026, 4, 20), 7),
			[date(2026, 5, 7), date(2026, 6, 7)],
		)

	def test_twelve_installments_split_1200_into_100_each(self):
		self.assertEqual(
			_split_amount(Decimal('1200.00'), 12),
			[Decimal('100.00')] * 12,
		)

	def make_product(self, ajustar_atrasadas=0):
		return SimpleNamespace(
			valor_total=Decimal('100.00'),
			dia_vencimento=15,
			ajustar_atrasadas=ajustar_atrasadas,
		)

	def make_installment(self, number, value, due_date):
		return SimpleNamespace(
			parcela_numero=number,
			valor=Decimal(value),
			dt_vencimento=due_date,
		)

	def test_cash_plan_uses_updated_total_and_next_due_day(self):
		result = _build_purchase_schedule(
			self.make_product(),
			1,
			[self.make_installment(1, '50.00', date(2026, 9, 15))],
			2,
			self.TODAY,
		)

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]['value'], Decimal('200.00'))
		self.assertEqual(result[0]['due_date'], date(2026, 10, 15))

	def test_installments_without_overdue_adjustment_split_total(self):
		source = [
			self.make_installment(1, '30.00', date(2026, 9, 15)),
			self.make_installment(2, '30.00', date(2026, 10, 15)),
			self.make_installment(3, '40.00', date(2026, 11, 15)),
		]

		result = _build_purchase_schedule(self.make_product(), 2, source, 1, self.TODAY)

		self.assertEqual([item['value'] for item in result], [Decimal('33.34'), Decimal('33.33'), Decimal('33.33')])
		self.assertEqual(
			[item['due_date'] for item in result],
			[date(2026, 10, 15), date(2026, 11, 15), date(2026, 12, 15)],
		)

	def test_installments_with_overdue_adjustment_split_all_source_value_over_upcoming_rows(self):
		source = [
			self.make_installment(number, '100.00', date(2026, month, 15))
			for number, month in enumerate(range(1, 13), start=1)
		]

		result = _build_purchase_schedule(
			self.make_product(1), 2, source, 1, date(2026, 10, 20)
		)

		self.assertEqual([item['value'] for item in result], [Decimal('600.00'), Decimal('600.00')])
		self.assertEqual(
			[item['due_date'] for item in result],
			[date(2026, 11, 15), date(2026, 12, 15)],
		)

	def test_entry_plan_adds_arrears_to_next_upcoming_and_keeps_other_values(self):
		source = [
			self.make_installment(number, '100.00', date(2026, month, 15))
			for number, month in enumerate(range(1, 13), start=1)
		]

		result = _build_purchase_schedule(
			self.make_product(1), 3, source, 1, date(2026, 10, 20)
		)

		self.assertEqual([item['value'] for item in result], [Decimal('1100.00'), Decimal('100.00')])
		self.assertEqual(
			[item['due_date'] for item in result],
			[date(2026, 11, 15), date(2026, 12, 15)],
		)

	def test_keep_overdue_dates_preserves_source_dates(self):
		product = self.make_product(2)
		source = [
			self.make_installment(1, '30.00', date(2026, 8, 20)),
			self.make_installment(2, '30.00', date(2026, 9, 15)),
			self.make_installment(3, '40.00', date(2026, 10, 15)),
		]

		result = _build_purchase_schedule(product, 2, source, 1, self.TODAY)

		self.assertEqual(
			[item['due_date'] for item in result],
			[date(2026, 8, 20), date(2026, 9, 15), date(2026, 10, 15)],
		)
