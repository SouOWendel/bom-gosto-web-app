from rest_framework import status
from rest_framework.test import APITestCase

from usuario.models import Usuario

from .models import Cliente, Produto

# testes de integracao da API de pedidos e da regra de acesso
class PedidoApiTests(APITestCase):
	
	# prepara usuario, cliente e produto para cada teste
	def setUp(self):
		self.usuario = Usuario.objects.create_user(
			login="teste-pedidos",
			password="senha-segura-para-teste",
			primeiro_acesso=False,
		)
		self.cliente = Cliente.objects.create(
			nome="Cliente de teste",
			telefone="11999990000",
		)
		self.produto = Produto.objects.create(
			nome="Produto de teste",
			preco_venda="12.50",
		)
		self.client.force_authenticate(user=self.usuario)

	# verifica criacao, consulta e atualizacao parcial do pedido
	def test_cria_consulta_e_atualiza_pedido(self):
		resposta = self.client.post(
			"/api/pedido/",
			{
				"tipo": "externo",
				"subtipo": "personalizado",
				"cliente": self.cliente.id_cliente,
				"valor_total": "12.50",
				"valor_sinal": "0.00",
				"itens": [
					{
						"produto": self.produto.id_produto,
						"quantidade": 1,
						"preco_unitario": "12.50",
					}
				],
			},
			format="json",
		)

		self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
		pedido_id = resposta.data["id_pedido"]

		consulta = self.client.get(f"/api/pedido/{pedido_id}/")
		self.assertEqual(consulta.status_code, status.HTTP_200_OK)
		self.assertEqual(len(consulta.data["itens"]), 1)

		atualizacao = self.client.patch(
			f"/api/pedido/{pedido_id}/",
			{"forma_pagamento": "pix"},
			format="json",
		)
		self.assertEqual(atualizacao.status_code, status.HTTP_200_OK)
		self.assertEqual(atualizacao.data["forma_pagamento"], "pix")

	# usuario que ainda precisa trocar a senha recebe HTTP 403
	def test_usuario_no_primeiro_acesso_nao_acessa_pedidos(self):
		self.usuario.primeiro_acesso = True
		self.usuario.save(update_fields=["primeiro_acesso"])

		resposta = self.client.get("/api/pedido/")

		self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
