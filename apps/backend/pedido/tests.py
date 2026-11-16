from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework import serializers
from rest_framework.test import APITestCase

from usuario.models import Usuario

from .models import Cliente, ItemPedido, Pedido, Produto, Receita
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

		listagem = self.client.get("/api/pedido/")
		self.assertEqual(listagem.status_code, status.HTTP_200_OK)
		self.assertEqual(len(listagem.data), 1)
		# a analise de producao fica no endpoint /validar/, fora da listagem
		self.assertNotIn("analise", listagem.data[0])

		atualizacao = self.client.patch(
			f"/api/pedido/{pedido_id}/",
			{"forma_pagamento": "pix"},
			format="json",
		)
		self.assertEqual(atualizacao.status_code, status.HTTP_200_OK)
		self.assertEqual(atualizacao.data["forma_pagamento"], "pix")

	# pedidos com o mesmo telefone reaproveitam o cliente existente
	def test_contato_com_mesmo_telefone_reaproveita_cliente(self):
		payload = {
			"tipo": "externo",
			"subtipo": "personalizado",
			"contato_nome": "Maria",
			"contato_telefone": self.cliente.telefone,
			"valor_total": "12.50",
			"valor_sinal": "0.00",
			"itens": [{"produto": self.produto.id_produto, "quantidade": 1, "preco_unitario": "12.50"}],
		}
		resposta = self.client.post("/api/pedido/", payload, format="json")
		self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
		self.assertEqual(resposta.data["cliente"], self.cliente.id_cliente)

		atualizacao = self.client.patch(
			f"/api/pedido/{resposta.data['id_pedido']}/",
			{"contato_nome": "Maria", "contato_telefone": self.cliente.telefone},
			format="json",
		)
		self.assertEqual(atualizacao.status_code, status.HTTP_200_OK)
		self.assertEqual(Cliente.objects.count(), 1)

	# pedido que passa de externo para interno deixa de ter cliente vinculado
	def test_pedido_que_vira_interno_perde_o_cliente(self):
		resposta = self.client.post(
			"/api/pedido/",
			{
				"tipo": "externo",
				"subtipo": "personalizado",
				"cliente": self.cliente.id_cliente,
				"valor_total": "12.50",
				"valor_sinal": "0.00",
				"itens": [{"produto": self.produto.id_produto, "quantidade": 1, "preco_unitario": "12.50"}],
			},
			format="json",
		)
		atualizacao = self.client.patch(
			f"/api/pedido/{resposta.data['id_pedido']}/",
			{"tipo": "interno", "subtipo": None, "valor_sinal": "0.00"},
			format="json",
		)
		self.assertEqual(atualizacao.status_code, status.HTTP_200_OK)
		self.assertIsNone(atualizacao.data["cliente"])

	# acoes em pedido inexistente devolvem 404 em vez de erro interno
	def test_acao_em_pedido_inexistente_retorna_404(self):
		for acao in ("consumir-estoque", "concluir", "cancelar"):
			resposta = self.client.post(f"/api/pedido/999999/{acao}/", {}, format="json")
			self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND, acao)

	# produto com pedido vinculado nao pode ser excluido e recebe 400
	def test_excluir_produto_vinculado_retorna_400(self):
		self.client.post(
			"/api/pedido/",
			{
				"tipo": "externo",
				"subtipo": "personalizado",
				"cliente": self.cliente.id_cliente,
				"valor_total": "12.50",
				"valor_sinal": "0.00",
				"itens": [{"produto": self.produto.id_produto, "quantidade": 1, "preco_unitario": "12.50"}],
			},
			format="json",
		)
		resposta = self.client.delete(f"/api/produtos/{self.produto.id_produto}/")
		self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

	# itens novos usam produto do catalogo; a receita vem do cadastro do produto
	def test_item_novo_exige_produto(self):
		receita = Receita.objects.create(nome="Receita", rendimento_quantidade="1")
		self.produto.receita = receita
		self.produto.save(update_fields=["receita"])
		pedido = {
			"tipo": "externo",
			"subtipo": "personalizado",
			"cliente": self.cliente.id_cliente,
			"valor_total": "10.00",
			"valor_sinal": "0.00",
			"itens": [{"receita": receita.id_receita, "quantidade": 1, "preco_unitario": "10.00"}],
		}
		resposta = self.client.post("/api/pedido/", pedido, format="json")
		self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("produto do catálogo", str(resposta.data))

	# pedido antigo com item de receita fica so para leitura
	def test_pedido_antigo_com_receita_nao_pode_ser_editado(self):
		receita = Receita.objects.create(nome="Receita antiga", rendimento_quantidade="1")
		pedido = Pedido.objects.create(tipo=Pedido.Tipo.INTERNO)
		ItemPedido.objects.create(pedido=pedido, receita=receita, quantidade=1, preco_unitario="0")
		resposta = self.client.patch(f"/api/pedido/{pedido.pk}/", {"data_entrega": "2026-12-01"}, format="json")
		self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("não podem ser editados", str(resposta.data))

	# sinal de pedido externo aceita a metade arredondada para cima nos centavos
	def test_sinal_aceita_metade_arredondada(self):
		resposta = self.client.post(
			"/api/pedido/",
			{
				"tipo": "externo",
				"subtipo": "personalizado",
				"cliente": self.cliente.id_cliente,
				"valor_total": "55.75",
				"valor_sinal": "27.88",
				"itens": [{"produto": self.produto.id_produto, "quantidade": 1, "preco_unitario": "55.75"}],
			},
			format="json",
		)
		self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)

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

    # verifica que um item de vitrine consulta a disponibilidade e encaminha para producao se o saldo for insuficiente
    def test_item_de_vitrine_consulta_servico_de_estoque(self):
        pedido = SimpleNamespace(
            tipo=Pedido.Tipo.EXTERNO,
            subtipo=Pedido.Subtipo.VITRINE,
        )
        item = SimpleNamespace(
            pedido=pedido,
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
            verificacao = ItemPedidoSerializer().get_verificacao_estoque(item)

        verificar.assert_called_once_with(12, 2)
        self.assertEqual(verificacao["quantidade_disponivel"], Decimal("1.00"))
        self.assertTrue(verificacao["encaminhar_para_producao"])

    # verifica que um item personalizado sem produto pronto é encaminhado para producao
    def test_item_personalizado_sem_produto_pronto_segue_para_producao(self):
        pedido = SimpleNamespace(
            tipo=Pedido.Tipo.EXTERNO,
            subtipo=Pedido.Subtipo.PERSONALIZADO,
        )
        item = SimpleNamespace(pedido=pedido, produto_id=None)

        verificacao = ItemPedidoSerializer().get_verificacao_estoque(item)

        self.assertFalse(verificacao["verificado"])
        self.assertTrue(verificacao["encaminhar_para_producao"])

    # verifica que um pedido interno nao consulta o servico de estoque para verificar a disponibilidade dos itens
    def test_pedido_interno_nao_consulta_estoque_para_cliente(self):
        pedido = SimpleNamespace(
            tipo=Pedido.Tipo.INTERNO,
            subtipo=None,
        )
        item = SimpleNamespace(pedido=pedido, produto_id=12, quantidade=2)

        verificacao = ItemPedidoSerializer().get_verificacao_estoque(item)

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


# garante que o seed prepara os dados do roteiro de demonstracao e pode ser repetido
class SeedDemonstracaoTests(APITestCase):
	def test_seed_prepara_roteiro_e_reset_restaura_os_pedidos(self):
		from io import StringIO

		from django.core.management import call_command

		from producao.services import analisar_pedido

		call_command("seed_desenvolvimento", stdout=StringIO())
		call_command("seed_desenvolvimento", stdout=StringIO())

		licilene = Pedido.objects.get(cliente__nome="Licilene Alves", status=Pedido.Status.PEDIDO_FEITO)
		analise = analisar_pedido(licilene)
		self.assertTrue(analise["encaminhar_para_producao"])
		self.assertEqual(analise["ausencias"], [])
		self.assertEqual(analise["ingredientes_insuficientes"], [])
		# o bolo do roteiro soma a massa (principal) e o recheio (complementar)
		self.assertEqual(
			{grupo["nome"] for grupo in analise["receitas"]},
			{"Massa branca", "Recheio delícia de limão"},
		)

		carlos = Pedido.objects.get(cliente__nome="Carlos Menezes", status=Pedido.Status.EM_PRODUCAO)
		self.assertTrue(analisar_pedido(carlos)["ingredientes"])

		licilene.status = Pedido.Status.CONCLUIDO
		licilene.save(update_fields=["status"])
		call_command("seed_desenvolvimento", "--resetar-demo", stdout=StringIO())
		licilene.refresh_from_db()
		self.assertEqual(licilene.status, Pedido.Status.PEDIDO_FEITO)
		self.assertEqual(Pedido.objects.filter(cliente__nome="Licilene Alves", status=Pedido.Status.PEDIDO_FEITO).count(), 1)


# receitas complementares do produto (RF18) sao gravadas pela API de produtos
class ProdutoReceitasComplementaresApiTests(APITestCase):
	def setUp(self):
		usuario = Usuario.objects.create_user(login="teste-produto-receitas", password="senha-de-teste-123", primeiro_acesso=False)
		self.client.force_authenticate(user=usuario)
		self.massa = Receita.objects.create(nome="Massa de chocolate", rendimento_quantidade="1")
		self.recheio = Receita.objects.create(nome="Recheio de brigadeiro", rendimento_quantidade="2")
		self.cobertura = Receita.objects.create(nome="Ganache", rendimento_quantidade="1")

	def test_cria_e_substitui_receitas_complementares(self):
		resposta = self.client.post(
			"/api/produtos/",
			{
				"nome": "Bolo de chocolate",
				"preco_venda": "80.00",
				"receita": self.massa.pk,
				"receitas_complementares": [
					{"receita": self.recheio.pk, "quantidade": "0.400", "unidade_medida": "kg"},
					{"receita": self.cobertura.pk, "quantidade": "0.300", "unidade_medida": "kg"},
				],
			},
			format="json",
		)
		self.assertEqual(resposta.status_code, status.HTTP_201_CREATED, resposta.data)
		nomes = {linha["receita_nome"] for linha in resposta.data["receitas_complementares"]}
		self.assertEqual(nomes, {"Recheio de brigadeiro", "Ganache"})

		produto_id = resposta.data["id_produto"]
		resposta = self.client.patch(
			f"/api/produtos/{produto_id}/",
			{"receitas_complementares": [{"receita": self.recheio.pk, "quantidade": "0.500", "unidade_medida": "kg"}]},
			format="json",
		)
		self.assertEqual(resposta.status_code, status.HTTP_200_OK, resposta.data)
		self.assertEqual(len(resposta.data["receitas_complementares"]), 1)
		self.assertEqual(resposta.data["receitas_complementares"][0]["quantidade"], "0.500")

		# editar so o preco preserva as complementares
		resposta = self.client.patch(f"/api/produtos/{produto_id}/", {"preco_venda": "90.00"}, format="json")
		self.assertEqual(len(resposta.data["receitas_complementares"]), 1)

	def test_recusa_principal_repetida_como_complementar(self):
		resposta = self.client.post(
			"/api/produtos/",
			{
				"nome": "Bolo",
				"preco_venda": "50.00",
				"receita": self.massa.pk,
				"receitas_complementares": [{"receita": self.massa.pk, "quantidade": "1", "unidade_medida": "un"}],
			},
			format="json",
		)
		self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("receitas_complementares", resposta.data)

	# o saldo do produto considera apenas lotes dentro da validade
	def test_saldo_disponivel_ignora_lotes_vencidos(self):
		from datetime import timedelta
		from django.utils import timezone
		from estoque.models import Estoque

		produto = Produto.objects.create(nome="Brigadeiro", preco_venda="2.00")
		hoje = timezone.localdate()
		Estoque.objects.create(produto=produto, quantidade_disponivel="5", data_validade=hoje + timedelta(days=3))
		Estoque.objects.create(produto=produto, quantidade_disponivel="3", data_validade=hoje - timedelta(days=1))
		resposta = self.client.get("/api/produtos/")
		saldo = next(p["saldo_disponivel"] for p in resposta.data if p["id_produto"] == produto.pk)
		self.assertEqual(Decimal(saldo), Decimal("5"))
