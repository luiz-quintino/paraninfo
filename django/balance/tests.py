from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase
from django.urls import reverse

from .views import _payment_history_summary


class PaymentHistorySummaryTests(SimpleTestCase):
	def test_payments_page_route_and_product_link_route_exist(self):
		self.assertEqual(
			reverse('balance:balance_my', kwargs={'usuario': 'associate-uuid'}),
			'/balance/balance-my/associate-uuid/',
		)
		self.assertEqual(
			reverse('products:product_my_list', kwargs={'UUID': 'associate-uuid'}),
			'/products/product-my-list/associate-uuid/',
		)

	def test_positive_balance_and_receipts_are_summarized(self):
		rows = [
			{'date': date(2026, 9, 1), 'paid': Decimal('150.00'), 'debit': Decimal('100.00'), 'received': Decimal('20.00')},
		]

		result = _payment_history_summary(rows, date(2026, 10, 2))

		self.assertEqual(result['balance'], Decimal('50.00'))
		self.assertEqual(result['total_received'], Decimal('20.00'))
		self.assertEqual(result['next_payment'], None)

		with_upcoming = _payment_history_summary(
			rows + [
				{'date': date(2026, 10, 15), 'paid': Decimal('0.00'), 'debit': Decimal('40.00'), 'received': Decimal('0.00')},
				{'date': date(2026, 10, 28), 'paid': Decimal('0.00'), 'debit': Decimal('25.00'), 'received': Decimal('0.00')},
				{'date': date(2026, 11, 15), 'paid': Decimal('0.00'), 'debit': Decimal('60.00'), 'received': Decimal('0.00')},
			],
			date(2026, 10, 2),
		)
		self.assertEqual(with_upcoming['next_debit'], Decimal('65.00'))
		self.assertEqual(with_upcoming['next_payment'], Decimal('65'))
		self.assertEqual(with_upcoming['next_payment_month'], 'Outubro')
		self.assertEqual(with_upcoming['grand_total_paid'], Decimal('150.00'))
		self.assertEqual(with_upcoming['grand_total_debit'], Decimal('225.00'))

	def test_negative_balance_computes_fine_interest_and_next_payment(self):
		rows = [
			{'date': date(2026, 9, 1), 'paid': Decimal('40.00'), 'debit': Decimal('100.00'), 'received': Decimal('0.00')},
			{'date': date(2026, 10, 15), 'paid': Decimal('0.00'), 'debit': Decimal('50.00'), 'received': Decimal('0.00')},
		]

		result = _payment_history_summary(rows, date(2026, 10, 2))

		self.assertEqual(result['balance'], Decimal('-60.00'))
		self.assertEqual(result['overdue_days'], 31)
		self.assertEqual(result['fine'], Decimal('1.20'))
		self.assertEqual(result['interest'], Decimal('6.14'))
		self.assertEqual(result['next_payment'], Decimal('117'))
		self.assertEqual(len(result['future_rows']), 1)
