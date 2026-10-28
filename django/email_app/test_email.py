from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from email_app.models import tbEmail
from email_app.views import email_detail
from users.models import tbAssociados


class EmailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sender', password='test')
        self.associado = tbAssociados.objects.create(
            uuid='sender-uuid', nome_responsavel='Remetente', email='sender@example.com',
            comissao=1, situacao='ativo', cpf='000', telefone='000',
            aluno='Aluno', nome_de_guerra='Guerra', codigo_associado='0001',
        )
        self.user.last_name = self.associado.uuid
        self.user.save()
        group = Group.objects.create(name='presidente')
        self.user.groups.add(group)

        self.recipient = tbAssociados.objects.create(
            uuid='recipient-uuid', nome_responsavel='Destinatário', email='dest@example.com',
            comissao=1, situacao='ativo', cpf='111', telefone='111',
            aluno='Aluno', nome_de_guerra='Guerra', codigo_associado='0002',
        )

    def _request(self, path, data=None):
        request = RequestFactory().post(path, data=data or {}) if data is not None else RequestFactory().get(path)
        request.user = self.user
        request.comissao = 1
        request.is_admin = True
        request.is_app_admin = False
        request.resolver_match = type('Resolver', (), {'url_name': 'email'})()
        request.session = {'user_data': {'sessao_id': 7, 'user_id': self.associado.id}}
        return request

    @patch('email_app.views.save_log', return_value=123)
    @patch('email_app.views.send_mail')
    def test_email_persists_distribution_and_sends(self, send_mail, save_log):
        from email_app.views import email

        request = self._request(reverse('email'), {
            'titulo': 'Aviso', 'conteudo': 'Informação', 'associados': [str(self.recipient.id)],
        })
        response = email(request)

        self.assertEqual(response.status_code, 302)
        record = tbEmail.objects.get()
        self.assertEqual(record.titulo, 'Aviso')
        self.assertEqual(record.distribuicao, f'["{self.recipient.id}"]')
        self.assertEqual(record.log_id, 123)
        send_mail.assert_called_once()

    def test_email_detail_returns_distribution_and_sender(self):
        record = tbEmail.objects.create(
            titulo='Aviso', conteudo='Informação', distribuicao='[' + str(self.recipient.id) + ']', log_id=999,
        )
        request = self._request(reverse('email_detail', args=[record.id]))
        request.is_admin = True

        response = email_detail(request, record.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['distribuicao'], ['Destinatário'])
