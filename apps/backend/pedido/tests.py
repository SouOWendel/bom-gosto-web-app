from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework import serializers
from rest_framework.test import APITestCase

from usuario.models import Usuario

from .models import Cliente, Pedido, Produto
from .serializers import ItemPedidoSerializer, PedidoSerializer

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
		self.analise_patch = patch(
			"pedido.serializers.analisar_pedido",
			return_value={"estoque": [], "receitas_sugeridas": [], "ausencias": [], "ingredientes_insuficientes": [], "ingredientes": [], "encaminhar_para_producao": False},
		)
		self.analise_patch.start()
		self.addCleanup(self.analise_patch.stop)
		self.estoque_patch = patch(
			"pedido.serializers.Estoque.objects.verificar_disponibilidade",
			return_value={"quantidade_solicitada": 1, "quantidade_disponivel": Decimal("0"), "disponivel": False, "encaminhar_para_producao": True},
		)
		self.estoque_patch.start()
		self.addCleanup(self.estoque_patch.stop)

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

# testes de integracao da API de pedidos com a consulta de disponibilidade do estoque
class PedidoEstoqueIntegrationTests(SimpleTestCase):

    def test_pedido_concluido_nao_pode_ser_editado(self):
        pedido = SimpleNamespace(status=Pedido.Status.CONCLUIDO)
        serializer = PedidoSerializer(instance=pedido)

        with self.assertRaises(serializers.ValidationError):
            serializer.validate({})

    # cria um serializer de item de pedido com o pedido fornecido para simular a chamada do serializer de pedido
    # o serializer é responsavel por transformar os dados do modelo em um formato que pode ser facilmente convertido em JSON e enviado para o cliente, alem de validar os dados recebidos do cliente antes de salvar no banco de dados
    def make_item_serializer(self, pedido):
        serializer = ItemPedidoSerializer()
        serializer.parent = SimpleNamespace(
            parent=SimpleNamespace(instance=pedido)
        )
        return serializer

    # verifica que um item de vitrine consulta a disponibilidade e encaminha para producao se o saldo for insuficiente
    def test_item_de_vitrine_consulta_servico_de_estoque(self):
        pedido = SimpleNamespace(
            tipo=Pedido.Tipo.EXTERNO,
            subtipo=Pedido.Subtipo.VITRINE,
        )
        item = SimpleNamespace(
            produto_id=12,
            quantidade=2,
            quantidade_peso=None,
        )
        resultado = {
            "quantidade_solicitada": 2,
            "quantidade_disponivel": Decimal("1.00"),
            "disponivel": False,
            "encaminhar_para_producao": True,
        }

        with patch(
            "estoque.models.Estoque.objects.verificar_disponibilidade",
            return_value=resultado,
        ) as verificar:
            verificacao = self.make_item_serializer(pedido).get_verificacao_estoque(
                item
            )

        verificar.assert_called_once_with(12, 2)
        self.assertEqual(verificacao["quantidade_disponivel"], Decimal("1.00"))
        self.assertTrue(verificacao["encaminhar_para_producao"])

    # verifica que um item personalizado sem produto pronto é encaminhado para producao
    def test_item_personalizado_sem_produto_pronto_segue_para_producao(self):
        pedido = SimpleNamespace(
            tipo=Pedido.Tipo.EXTERNO,
            subtipo=Pedido.Subtipo.PERSONALIZADO,
        )
        item = SimpleNamespace(produto_id=None)

        verificacao = self.make_item_serializer(pedido).get_verificacao_estoque(item)

        self.assertFalse(verificacao["verificado"])
        self.assertTrue(verificacao["encaminhar_para_producao"])

    # verifica que um pedido interno nao consulta o servico de estoque para verificar a disponibilidade dos itens
    def test_pedido_interno_nao_consulta_estoque_para_cliente(self):
        pedido = SimpleNamespace(
            tipo=Pedido.Tipo.INTERNO,
            subtipo=None,
        )
        item = SimpleNamespace(produto_id=12, quantidade=2)

        verificacao = self.make_item_serializer(pedido).get_verificacao_estoque(item)

        self.assertIsNone(verificacao)

    # verifica que um pedido de vitrine exige que os itens referenciem produtos prontos e nao permite itens sem produto pronto
    def test_pedido_de_vitrine_exige_produto_pronto(self):
        serializer = PedidoSerializer()

        with self.assertRaises(serializers.ValidationError):
            serializer.validate(
                {
                    "tipo": Pedido.Tipo.EXTERNO,
                    "subtipo": Pedido.Subtipo.VITRINE,
                    "cliente": object(),
                    "itens": [{"produto": None, "receita": object()}],
                }
            )
