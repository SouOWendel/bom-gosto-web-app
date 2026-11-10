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

		listagem = self.client.get("/api/pedido/")
		self.assertEqual(listagem.status_code, status.HTTP_200_OK)
		self.assertEqual(len(listagem.data), 1)

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
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient, APITestCase

from usuario.models import Usuario

from .models import Cancelamento, Cliente, ItemPedido, Pedido, Produto, Receita
from .serializers import (
    CancelamentoRegistroSerializer,
    ItemPedidoSerializer,
    PedidoSerializer,
    ProdutoSerializer,
)
from .views import CancelamentoViewSet

# testes complementares do modulo Pedido (validacoes, acoes operacionais, produtos, cancelamentos e acesso)
# os testes de serializer nao usam banco; os de API seguem o mesmo preparo dos testes ja existentes em tests.py


# ---------- apoio ----------

def _atributos_pedido(**extras):
    atributos = {
        "tipo": Pedido.Tipo.INTERNO,
        "valor_total": Decimal("10.00"),
        "valor_sinal": Decimal("0.00"),
        "itens": [{"produto": object(), "receita": None}],
    }
    atributos.update(extras)
    return atributos


def _atributos_externo(**extras):
    return _atributos_pedido(
        tipo=Pedido.Tipo.EXTERNO,
        subtipo=Pedido.Subtipo.PERSONALIZADO,
        cliente=object(),
        **extras,
    )


def _pedido_existente(estado, **extras):
    dados = {
        "status": estado,
        "tipo": Pedido.Tipo.EXTERNO,
        "subtipo": Pedido.Subtipo.PERSONALIZADO,
        "cliente": object(),
        "valor_total": Decimal("10.00"),
        "valor_sinal": Decimal("0.00"),
    }
    dados.update(extras)
    return SimpleNamespace(**dados)


# ---------- PedidoSerializer.validate ----------

class PedidoSerializerRegrasTests(SimpleTestCase):
    def test_pedido_externo_exige_cliente_ou_contato_completo(self):
        casos = (
            _atributos_pedido(tipo=Pedido.Tipo.EXTERNO, subtipo=Pedido.Subtipo.PERSONALIZADO),
            _atributos_pedido(
                tipo=Pedido.Tipo.EXTERNO,
                subtipo=Pedido.Subtipo.PERSONALIZADO,
                contato_nome="Maria",
            ),
            _atributos_pedido(
                tipo=Pedido.Tipo.EXTERNO,
                subtipo=Pedido.Subtipo.PERSONALIZADO,
                contato_telefone="11999990000",
            ),
        )
        for atributos in casos:
            with self.subTest(atributos=sorted(atributos)):
                with self.assertRaises(ValidationError) as erro:
                    PedidoSerializer().validate(atributos)

                self.assertIn("cliente", erro.exception.detail)

    def test_pedido_externo_aceita_cliente_ou_contato_completo(self):
        com_cliente = _atributos_externo()
        com_contato = _atributos_pedido(
            tipo=Pedido.Tipo.EXTERNO,
            subtipo=Pedido.Subtipo.PERSONALIZADO,
            contato_nome="Maria",
            contato_telefone="11999990000",
        )

        self.assertEqual(PedidoSerializer().validate(com_cliente), com_cliente)
        self.assertEqual(PedidoSerializer().validate(com_contato), com_contato)

    def test_pedido_externo_exige_subtipo(self):
        atributos = _atributos_pedido(tipo=Pedido.Tipo.EXTERNO, cliente=object())

        with self.assertRaises(ValidationError) as erro:
            PedidoSerializer().validate(atributos)

        self.assertIn("subtipo", erro.exception.detail)

    def test_pedido_interno_nao_aceita_subtipo(self):
        atributos = _atributos_pedido(subtipo=Pedido.Subtipo.VITRINE)

        with self.assertRaises(ValidationError) as erro:
            PedidoSerializer().validate(atributos)

        self.assertIn("subtipo", erro.exception.detail)

    def test_pedido_novo_exige_ao_menos_um_item(self):
        for atributos in (_atributos_pedido(itens=[]), {"tipo": Pedido.Tipo.INTERNO}):
            with self.subTest(atributos=sorted(atributos)):
                with self.assertRaises(ValidationError) as erro:
                    PedidoSerializer().validate(atributos)

                self.assertIn("itens", erro.exception.detail)

    def test_atualizacao_nao_aceita_lista_de_itens_vazia(self):
        serializer = PedidoSerializer(instance=_pedido_existente(Pedido.Status.EM_PRODUCAO))

        with self.assertRaises(ValidationError) as erro:
            serializer.validate({"itens": []})

        self.assertIn("itens", erro.exception.detail)

    def test_atualizacao_sem_itens_preserva_os_existentes(self):
        serializer = PedidoSerializer(instance=_pedido_existente(Pedido.Status.PEDIDO_FEITO))

        self.assertEqual(serializer.validate({"forma_pagamento": "pix"}), {"forma_pagamento": "pix"})

    def test_pedido_personalizado_aceita_item_apenas_com_receita(self):
        atributos = _atributos_externo(itens=[{"produto": None, "receita": object()}])

        self.assertEqual(PedidoSerializer().validate(atributos), atributos)

    def test_pedido_de_vitrine_aceita_itens_com_produto(self):
        atributos = _atributos_pedido(
            tipo=Pedido.Tipo.EXTERNO,
            subtipo=Pedido.Subtipo.VITRINE,
            cliente=object(),
            itens=[{"produto": object(), "receita": None}],
        )

        self.assertEqual(PedidoSerializer().validate(atributos), atributos)

    def test_rejeita_valores_negativos(self):
        casos = {
            "valor_total": {"valor_total": Decimal("-1.00"), "valor_sinal": Decimal("0.00")},
            "valor_sinal": {"valor_sinal": Decimal("-1.00")},
        }
        for campo, valores in casos.items():
            with self.subTest(campo=campo):
                with self.assertRaises(ValidationError) as erro:
                    PedidoSerializer().validate(_atributos_pedido(**valores))

                self.assertIn(campo, erro.exception.detail)

    def test_sinal_nao_pode_ser_maior_que_o_total(self):
        with self.assertRaises(ValidationError) as erro:
            PedidoSerializer().validate(_atributos_pedido(valor_sinal=Decimal("10.01")))

        self.assertIn("valor_sinal", erro.exception.detail)

    def test_pedido_interno_aceita_qualquer_sinal_ate_o_total(self):
        atributos = _atributos_pedido(valor_sinal=Decimal("3.00"))

        self.assertEqual(PedidoSerializer().validate(atributos), atributos)

    def test_pedido_externo_aceita_sinal_zero_ou_metade_do_total(self):
        for sinal in (Decimal("0.00"), Decimal("5.00")):
            with self.subTest(sinal=sinal):
                atributos = _atributos_externo(valor_sinal=sinal)

                self.assertEqual(PedidoSerializer().validate(atributos), atributos)

    def test_pedido_externo_rejeita_sinal_diferente_de_zero_ou_metade(self):
        with self.assertRaises(ValidationError) as erro:
            PedidoSerializer().validate(_atributos_externo(valor_sinal=Decimal("3.00")))

        self.assertIn("valor_sinal", erro.exception.detail)

    def test_metade_do_total_e_arredondada_para_centavos_com_meio_para_cima(self):
        total = Decimal("10.01")  # metade exata: 5,005 -> 5,01

        aceito = _atributos_externo(valor_total=total, valor_sinal=Decimal("5.01"))
        self.assertEqual(PedidoSerializer().validate(aceito), aceito)

        with self.assertRaises(ValidationError) as erro:
            PedidoSerializer().validate(_atributos_externo(valor_total=total, valor_sinal=Decimal("5.00")))
        self.assertIn("valor_sinal", erro.exception.detail)

    def test_atualizacao_herda_tipo_total_e_sinal_do_pedido_existente(self):
        serializer = PedidoSerializer(instance=_pedido_existente(Pedido.Status.EM_PRODUCAO))

        self.assertEqual(serializer.validate({"valor_sinal": Decimal("5.00")}), {"valor_sinal": Decimal("5.00")})
        self.assertEqual(serializer.validate({"valor_total": Decimal("20.00")}), {"valor_total": Decimal("20.00")})
        with self.assertRaises(ValidationError) as erro:
            serializer.validate({"valor_sinal": Decimal("3.00")})
        self.assertIn("valor_sinal", erro.exception.detail)

    def test_pedido_concluido_ou_cancelado_nao_pode_ser_editado(self):
        estados = (
            Pedido.Status.CANCELADO,
            "pedido_concluido",
            "pedido_cancelado",
        )
        for estado in estados:
            with self.subTest(estado=estado):
                serializer = PedidoSerializer(instance=_pedido_existente(estado))

                with self.assertRaises(ValidationError) as erro:
                    serializer.validate({})

                self.assertIn("status", erro.exception.detail)

    def test_pedido_feito_ou_em_producao_pode_ser_editado(self):
        for estado in (Pedido.Status.PEDIDO_FEITO, Pedido.Status.EM_PRODUCAO, "pagamento_parcial"):
            with self.subTest(estado=estado):
                serializer = PedidoSerializer(instance=_pedido_existente(estado))

                self.assertEqual(serializer.validate({}), {})


# ---------- ItemPedidoSerializer ----------

class ItemPedidoSerializerRegrasTests(SimpleTestCase):
    @staticmethod
    def _item(**extras):
        atributos = {"produto": object(), "quantidade": 2, "preco_unitario": Decimal("5.00")}
        atributos.update(extras)
        return atributos

    def test_aceita_item_com_produto_e_quantidade(self):
        atributos = self._item()

        self.assertEqual(ItemPedidoSerializer().validate(atributos), atributos)

    def test_aceita_item_com_receita_e_peso(self):
        atributos = {"receita": object(), "quantidade_peso": Decimal("1.50")}

        self.assertEqual(ItemPedidoSerializer().validate(atributos), atributos)

    def test_exige_exatamente_um_entre_produto_e_receita(self):
        casos = (
            self._item(produto=None),
            self._item(produto=object(), receita=object()),
        )
        for atributos in casos:
            with self.subTest(atributos=sorted(atributos)):
                with self.assertRaises(ValidationError):
                    ItemPedidoSerializer().validate(atributos)

    def test_exige_quantidade_ou_peso(self):
        with self.assertRaises(ValidationError):
            ItemPedidoSerializer().validate(self._item(quantidade=None))

    def test_rejeita_quantidade_e_peso_nao_positivos(self):
        casos = (
            ("quantidade", self._item(quantidade=0)),
            ("quantidade", self._item(quantidade=-1)),
            ("quantidade_peso", self._item(quantidade=None, quantidade_peso=Decimal("0"))),
            ("quantidade_peso", self._item(quantidade=None, quantidade_peso=Decimal("-0.50"))),
        )
        for campo, atributos in casos:
            with self.subTest(campo=campo, atributos=atributos):
                with self.assertRaises(ValidationError) as erro:
                    ItemPedidoSerializer().validate(atributos)

                self.assertIn(campo, erro.exception.detail)

    def test_rejeita_preco_e_custo_negativos(self):
        casos = (
            ("preco_unitario", self._item(preco_unitario=Decimal("-0.01"))),
            ("custo_unitario", self._item(custo_unitario=Decimal("-0.01"))),
        )
        for campo, atributos in casos:
            with self.subTest(campo=campo):
                with self.assertRaises(ValidationError) as erro:
                    ItemPedidoSerializer().validate(atributos)

                self.assertIn(campo, erro.exception.detail)

    def test_aceita_preco_e_custo_zerados(self):
        atributos = self._item(preco_unitario=Decimal("0.00"), custo_unitario=Decimal("0.00"))

        self.assertEqual(ItemPedidoSerializer().validate(atributos), atributos)


class VerificacaoEstoqueRegrasTests(SimpleTestCase):
    @staticmethod
    def _item(subtipo=Pedido.Subtipo.VITRINE, **extras):
        pedido = SimpleNamespace(tipo=Pedido.Tipo.EXTERNO, subtipo=subtipo)
        dados = {"pedido": pedido, "produto_id": 12, "quantidade": 2, "quantidade_peso": None}
        dados.update(extras)
        return SimpleNamespace(**dados)

    def test_item_atendido_pelo_estoque_e_marcado_como_verificado(self):
        resultado = {
            "quantidade_solicitada": 2,
            "quantidade_disponivel": Decimal("5.00"),
            "disponivel": True,
            "encaminhar_para_producao": False,
        }
        with patch("pedido.serializers.Estoque.objects.verificar_disponibilidade", return_value=resultado):
            verificacao = ItemPedidoSerializer().get_verificacao_estoque(self._item())

        self.assertTrue(verificacao["verificado"])
        self.assertTrue(verificacao["disponivel"])
        self.assertFalse(verificacao["encaminhar_para_producao"])

    def test_usa_o_peso_quando_nao_ha_quantidade(self):
        with patch(
            "pedido.serializers.Estoque.objects.verificar_disponibilidade",
            return_value={"disponivel": True},
        ) as verificar:
            ItemPedidoSerializer().get_verificacao_estoque(
                self._item(quantidade=None, quantidade_peso=Decimal("1.50"))
            )

        verificar.assert_called_once_with(12, Decimal("1.50"))

    def test_item_sem_quantidade_nem_peso_nao_e_verificado(self):
        with patch("pedido.serializers.Estoque.objects.verificar_disponibilidade") as verificar:
            verificacao = ItemPedidoSerializer().get_verificacao_estoque(
                self._item(quantidade=None, quantidade_peso=None)
            )

        verificar.assert_not_called()
        self.assertFalse(verificacao["verificado"])
        self.assertIsNone(verificacao["disponivel"])
        self.assertIsNone(verificacao["encaminhar_para_producao"])

    def test_pedido_externo_personalizado_tambem_consulta_o_estoque(self):
        with patch(
            "pedido.serializers.Estoque.objects.verificar_disponibilidade",
            return_value={"disponivel": False},
        ) as verificar:
            verificacao = ItemPedidoSerializer().get_verificacao_estoque(
                self._item(subtipo=Pedido.Subtipo.PERSONALIZADO)
            )

        verificar.assert_called_once_with(12, 2)
        self.assertTrue(verificacao["verificado"])

    def test_item_sem_pedido_ou_sem_subtipo_nao_tem_verificacao(self):
        sem_pedido = SimpleNamespace(pedido=None)
        sem_subtipo = self._item(subtipo=None)

        self.assertIsNone(ItemPedidoSerializer().get_verificacao_estoque(sem_pedido))
        self.assertIsNone(ItemPedidoSerializer().get_verificacao_estoque(sem_subtipo))


# ---------- ProdutoSerializer e CancelamentoRegistroSerializer ----------

class ProdutoSerializerTests(SimpleTestCase):
    def test_preco_de_venda_nao_pode_ser_negativo(self):
        serializer = ProdutoSerializer()

        with self.assertRaises(ValidationError):
            serializer.validate_preco_venda(Decimal("-0.01"))
        self.assertEqual(serializer.validate_preco_venda(Decimal("0")), Decimal("0"))

    def test_aceita_produto_sem_receita(self):
        serializer = ProdutoSerializer(data={"nome": "Brigadeiro", "preco_venda": "3.50"})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_exige_nome_e_preco(self):
        serializer = ProdutoSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("nome", serializer.errors)
        self.assertIn("preco_venda", serializer.errors)

    def test_rejeita_nome_maior_que_cem_caracteres(self):
        serializer = ProdutoSerializer(data={"nome": "a" * 101, "preco_venda": "3.50"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("nome", serializer.errors)


class CancelamentoRegistroSerializerTests(SimpleTestCase):
    def test_representa_o_registro_de_cancelamento(self):
        cancelamento = Cancelamento(
            id_cancelamento=1,
            pedido_id=5,
            destino="descarte",
            data_cancelamento=date(2026, 11, 10),
        )

        dados = CancelamentoRegistroSerializer(cancelamento).data

        self.assertEqual(
            dict(dados),
            {
                "id_cancelamento": 1,
                "pedido": 5,
                "destino": "descarte",
                "data_cancelamento": "2026-11-10",
            },
        )


# ---------- API: preparo comum ----------

# mesmo preparo dos testes existentes: usuario autenticado, cliente, produto e servicos de analise simulados
class _PedidoApiBase(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            login="teste-pedidos-regras",
            password="senha-segura-para-teste",
            primeiro_acesso=False,
        )
        self.cliente = Cliente.objects.create(nome="Cliente de teste", telefone="11999990000")
        self.produto = Produto.objects.create(nome="Produto de teste", preco_venda="12.50")
        self.client.force_authenticate(user=self.usuario)
        analise = patch(
            "pedido.serializers.analisar_pedido",
            return_value={
                "estoque": [],
                "receitas_sugeridas": [],
                "ausencias": [],
                "ingredientes_insuficientes": [],
                "ingredientes": [],
                "encaminhar_para_producao": False,
            },
        )
        analise.start()
        self.addCleanup(analise.stop)
        estoque = patch(
            "pedido.serializers.Estoque.objects.verificar_disponibilidade",
            return_value={
                "quantidade_solicitada": 1,
                "quantidade_disponivel": Decimal("0"),
                "disponivel": False,
                "encaminhar_para_producao": True,
            },
        )
        estoque.start()
        self.addCleanup(estoque.stop)

    def _item(self, **extras):
        item = {"produto": self.produto.id_produto, "quantidade": 1, "preco_unitario": "12.50"}
        item.update(extras)
        return item

    def _payload(self, **extras):
        dados = {
            "tipo": "interno",
            "valor_total": "12.50",
            "valor_sinal": "0.00",
            "itens": [self._item()],
        }
        dados.update(extras)
        return dados

    def _criar_pedido(
        self,
        estado=Pedido.Status.PEDIDO_FEITO,
        tipo=Pedido.Tipo.INTERNO,
        subtipo=None,
        com_item=True,
    ):
        pedido = Pedido.objects.create(
            tipo=tipo,
            subtipo=subtipo,
            status=estado,
            valor_total=Decimal("12.50"),
            valor_sinal=Decimal("0.00"),
        )
        if com_item:
            ItemPedido.objects.create(
                pedido=pedido,
                produto=self.produto,
                quantidade=2,
                preco_unitario=Decimal("12.50"),
            )
        return pedido

    def _criar_externo(self, estado=Pedido.Status.PEDIDO_FEITO, **extras):
        return self._criar_pedido(
            estado=estado,
            tipo=Pedido.Tipo.EXTERNO,
            subtipo=Pedido.Subtipo.PERSONALIZADO,
            **extras,
        )


# ---------- API: cadastro e edicao de pedidos ----------

class PedidoCadastroApiTests(_PedidoApiBase):
    def test_cria_pedido_interno_sem_cliente_com_status_inicial(self):
        resposta = self.client.post("/api/pedido/", self._payload(), format="json")

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["status"], "pedido_feito")
        self.assertIsNone(resposta.data["cliente"])
        self.assertEqual(ItemPedido.objects.filter(pedido_id=resposta.data["id_pedido"]).count(), 1)

    def test_status_enviado_no_cadastro_e_ignorado(self):
        resposta = self.client.post("/api/pedido/", self._payload(status="concluido"), format="json")

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["status"], "pedido_feito")

    def test_cria_cliente_a_partir_do_contato_informado(self):
        payload = self._payload(
            tipo="externo",
            subtipo="personalizado",
            contato_nome="Maria Souza",
            contato_telefone="11988887777",
        )

        resposta = self.client.post("/api/pedido/", payload, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        novo_cliente = Cliente.objects.get(nome="Maria Souza", telefone="11988887777")
        self.assertEqual(resposta.data["cliente"], novo_cliente.id_cliente)

    def test_rejeita_pedido_externo_sem_cliente_nem_contato(self):
        payload = self._payload(tipo="externo", subtipo="personalizado")

        resposta = self.client.post("/api/pedido/", payload, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", resposta.data)

    def test_rejeita_pedido_sem_itens(self):
        resposta = self.client.post("/api/pedido/", self._payload(itens=[]), format="json")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("itens", resposta.data)

    def test_rejeita_item_sem_produto_e_sem_receita(self):
        payload = self._payload(itens=[{"quantidade": 1, "preco_unitario": "12.50"}])

        resposta = self.client.post("/api/pedido/", payload, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("itens", resposta.data)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_rejeita_sinal_diferente_de_zero_ou_metade_em_pedido_externo(self):
        payload = self._payload(
            tipo="externo",
            subtipo="personalizado",
            cliente=self.cliente.id_cliente,
            valor_sinal="3.00",
        )

        resposta = self.client.post("/api/pedido/", payload, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("valor_sinal", resposta.data)

    def test_aceita_sinal_de_metade_do_total_em_pedido_externo(self):
        payload = self._payload(
            tipo="externo",
            subtipo="personalizado",
            cliente=self.cliente.id_cliente,
            valor_sinal="6.25",
        )

        resposta = self.client.post("/api/pedido/", payload, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["valor_sinal"], "6.25")

    def test_listagem_mostra_os_pedidos_mais_recentes_primeiro(self):
        antigo = self._criar_pedido()
        recente = self._criar_pedido()

        resposta = self.client.get("/api/pedido/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [pedido["id_pedido"] for pedido in resposta.data],
            [recente.id_pedido, antigo.id_pedido],
        )

    def test_atualizacao_sem_itens_preserva_os_itens_existentes(self):
        pedido = self._criar_pedido()

        resposta = self.client.patch(f"/api/pedido/{pedido.id_pedido}/", {"forma_pagamento": "pix"}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(ItemPedido.objects.filter(pedido=pedido).count(), 1)

    def test_atualizacao_com_itens_substitui_os_itens_anteriores(self):
        pedido = self._criar_pedido()
        itens = [self._item(), self._item(quantidade=3)]

        resposta = self.client.patch(f"/api/pedido/{pedido.id_pedido}/", {"itens": itens}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(ItemPedido.objects.filter(pedido=pedido).count(), 2)

    def test_atualizacao_com_lista_de_itens_vazia_e_rejeitada(self):
        pedido = self._criar_pedido()

        resposta = self.client.patch(f"/api/pedido/{pedido.id_pedido}/", {"itens": []}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ItemPedido.objects.filter(pedido=pedido).count(), 1)

    def test_pedido_concluido_ou_cancelado_nao_aceita_edicao(self):
        for estado in (Pedido.Status.CONCLUIDO, Pedido.Status.CANCELADO, "pedido_concluido"):
            with self.subTest(estado=estado):
                pedido = self._criar_pedido(estado=estado)

                resposta = self.client.patch(
                    f"/api/pedido/{pedido.id_pedido}/", {"forma_pagamento": "pix"}, format="json"
                )

                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("status", resposta.data)

    def test_exibe_status_legado_como_etapa_operacional_atual(self):
        legado = {
            "pagamento_parcial": "em_producao",
            "pagamento_total": "pedido_feito",
            "pedido_em_producao": "em_producao",
            "pedido_concluido": "concluido",
            "pedido_cancelado": "cancelado",
        }
        for antigo, atual in legado.items():
            with self.subTest(status_antigo=antigo):
                pedido = self._criar_pedido(estado=antigo)

                resposta = self.client.get(f"/api/pedido/{pedido.id_pedido}/")

                self.assertEqual(resposta.data["status"], atual)

    def test_nao_disponibiliza_exclusao_de_pedido(self):
        pedido = self._criar_pedido()

        resposta = self.client.delete(f"/api/pedido/{pedido.id_pedido}/")

        self.assertEqual(resposta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())


# ---------- API: acoes consumir-estoque, concluir e cancelar ----------

class PedidoConsumirEstoqueApiTests(_PedidoApiBase):
    def _consumir(self, pedido):
        return self.client.post(f"/api/pedido/{pedido.id_pedido}/consumir-estoque/", {}, format="json")

    def test_da_baixa_nos_lotes_e_conclui_o_pedido_externo(self):
        for estado in (Pedido.Status.PEDIDO_FEITO, Pedido.Status.PRODUCAO_CONCLUIDA):
            with self.subTest(estado=estado):
                pedido = self._criar_externo(estado=estado)
                with patch("pedido.views.baixar_lotes") as baixar:
                    resposta = self._consumir(pedido)

                self.assertEqual(resposta.status_code, status.HTTP_200_OK)
                self.assertEqual(resposta.data["status"], "concluido")
                baixar.assert_called_once_with(self.produto.pk, Decimal("2"))
                pedido.refresh_from_db()
                self.assertEqual(pedido.status, Pedido.Status.CONCLUIDO)

    def test_usa_o_peso_quando_o_item_nao_tem_quantidade(self):
        pedido = self._criar_externo(com_item=False)
        ItemPedido.objects.create(
            pedido=pedido,
            produto=self.produto,
            quantidade=None,
            quantidade_peso=Decimal("1.50"),
            preco_unitario=Decimal("12.50"),
        )

        with patch("pedido.views.baixar_lotes") as baixar:
            resposta = self._consumir(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        baixar.assert_called_once_with(self.produto.pk, Decimal("1.50"))

    def test_item_so_com_receita_usa_o_produto_da_receita(self):
        receita = Receita.objects.create(nome="Bolo de cenoura")
        produto_da_receita = Produto.objects.create(nome="Bolo pronto", preco_venda="30.00", receita=receita)
        pedido = self._criar_externo(com_item=False)
        ItemPedido.objects.create(pedido=pedido, receita=receita, quantidade=1, preco_unitario=Decimal("30.00"))

        with patch("pedido.views.baixar_lotes") as baixar:
            resposta = self._consumir(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        baixar.assert_called_once_with(produto_da_receita.pk, Decimal("1"))

    def test_item_so_com_receita_usa_a_relacao_receita_produto_quando_nao_ha_produto_direto(self):
        receita = Receita.objects.create(nome="Torta")
        produto_relacionado = Produto.objects.create(nome="Torta pronta", preco_venda="40.00")
        pedido = self._criar_externo(com_item=False)
        ItemPedido.objects.create(pedido=pedido, receita=receita, quantidade=1, preco_unitario=Decimal("40.00"))

        with (
            patch("pedido.models.ReceitaProduto.objects.filter") as relacao,
            patch("pedido.views.baixar_lotes") as baixar,
        ):
            relacao.return_value.select_related.return_value.first.return_value = SimpleNamespace(
                produto=produto_relacionado
            )
            resposta = self._consumir(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        baixar.assert_called_once_with(produto_relacionado.pk, Decimal("1"))

    def test_rejeita_item_sem_produto_pronto_associado(self):
        receita = Receita.objects.create(nome="Receita sem produto")
        pedido = self._criar_externo(com_item=False)
        ItemPedido.objects.create(pedido=pedido, receita=receita, quantidade=1, preco_unitario=Decimal("10.00"))

        with (
            patch("pedido.models.ReceitaProduto.objects.filter") as relacao,
            patch("pedido.views.baixar_lotes") as baixar,
        ):
            relacao.return_value.select_related.return_value.first.return_value = None
            resposta = self._consumir(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("itens", resposta.data)
        baixar.assert_not_called()
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.PEDIDO_FEITO)

    def test_recusa_consumo_em_pedido_interno(self):
        pedido = self._criar_pedido()

        with patch("pedido.views.baixar_lotes") as baixar:
            resposta = self._consumir(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tipo", resposta.data)
        baixar.assert_not_called()

    def test_recusa_consumo_fora_de_pedido_feito_ou_producao_concluida(self):
        for estado in (Pedido.Status.EM_PRODUCAO, Pedido.Status.CONCLUIDO, Pedido.Status.CANCELADO):
            with self.subTest(estado=estado):
                pedido = self._criar_externo(estado=estado)

                with patch("pedido.views.baixar_lotes") as baixar:
                    resposta = self._consumir(pedido)

                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("status", resposta.data)
                baixar.assert_not_called()

    def test_falha_na_baixa_de_lotes_mantem_o_status_do_pedido(self):
        pedido = self._criar_externo()

        with patch(
            "pedido.views.baixar_lotes",
            side_effect=ValidationError({"quantidade": "Estoque insuficiente."}),
        ):
            resposta = self._consumir(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.PEDIDO_FEITO)


class PedidoConcluirApiTests(_PedidoApiBase):
    def _concluir(self, pedido):
        return self.client.post(f"/api/pedido/{pedido.id_pedido}/concluir/", {}, format="json")

    def test_conclui_reposicao_interna_com_producao_finalizada(self):
        pedido = self._criar_pedido(estado=Pedido.Status.PRODUCAO_CONCLUIDA)

        resposta = self._concluir(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], "concluido")
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.CONCLUIDO)

    def test_recusa_conclusao_de_pedido_interno_antes_de_finalizar_a_producao(self):
        estados = (
            Pedido.Status.PEDIDO_FEITO,
            Pedido.Status.EM_PRODUCAO,
            Pedido.Status.CONCLUIDO,
            Pedido.Status.CANCELADO,
        )
        for estado in estados:
            with self.subTest(estado=estado):
                pedido = self._criar_pedido(estado=estado)

                resposta = self._concluir(pedido)

                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("status", resposta.data)
                pedido.refresh_from_db()
                self.assertEqual(pedido.status, estado)

    def test_recusa_conclusao_direta_de_pedido_externo(self):
        pedido = self._criar_externo(estado=Pedido.Status.PRODUCAO_CONCLUIDA)

        resposta = self._concluir(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.PRODUCAO_CONCLUIDA)


class PedidoCancelarApiTests(_PedidoApiBase):
    def _cancelar(self, pedido, payload):
        return self.client.post(f"/api/pedido/{pedido.id_pedido}/cancelar/", payload, format="json")

    def test_rejeita_destino_desconhecido(self):
        pedido = self._criar_pedido()

        resposta = self._cancelar(pedido, {"consumos": [], "destino": "doacao"})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("destino", resposta.data)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.PEDIDO_FEITO)

    def test_destino_estoque_exige_produto_aproveitado(self):
        pedido = self._criar_pedido()

        resposta = self._cancelar(pedido, {"consumos": [], "destino": "estoque"})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("produto_aproveitado", resposta.data)

    def test_exige_a_lista_de_consumos(self):
        pedido = self._criar_pedido()

        resposta = self._cancelar(pedido, {"destino": "descarte"})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("consumos", resposta.data)

    def test_devolve_o_registro_de_cancelamento_e_o_pedido_cancelado(self):
        pedido = self._criar_pedido()
        payload = {"consumos": [], "destino": "descarte"}
        pedido_cancelado = Pedido.objects.get(pk=pedido.pk)
        pedido_cancelado.status = Pedido.Status.CANCELADO
        cancelamento = Cancelamento(
            id_cancelamento=1,
            pedido_id=pedido.pk,
            destino="descarte",
            data_cancelamento=date(2026, 11, 10),
        )

        with patch("pedido.views.CancelamentoSerializer") as classe:
            classe.return_value.save.return_value = (pedido_cancelado, cancelamento)
            resposta = self._cancelar(pedido, payload)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["cancelamento"]["destino"], "descarte")
        self.assertEqual(resposta.data["cancelamento"]["pedido"], pedido.pk)
        self.assertEqual(resposta.data["pedido"]["status"], "cancelado")
        self.assertEqual(classe.call_args.kwargs["data"], payload)
        self.assertEqual(classe.call_args.kwargs["context"]["pedido"].pk, pedido.pk)
        classe.return_value.is_valid.assert_called_once_with(raise_exception=True)


# ---------- API: cancelamentos (somente leitura) ----------

class CancelamentoApiTests(_PedidoApiBase):
    def _registro(self):
        return Cancelamento(
            id_cancelamento=1,
            pedido_id=5,
            destino="descarte",
            data_cancelamento=date(2026, 11, 10),
        )

    def test_lista_os_cancelamentos_registrados(self):
        with patch.object(CancelamentoViewSet, "get_queryset", return_value=[self._registro()]):
            resposta = self.client.get("/api/cancelamento/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resposta.data), 1)
        self.assertEqual(resposta.data[0]["destino"], "descarte")
        self.assertEqual(resposta.data[0]["pedido"], 5)

    def test_consulta_um_cancelamento(self):
        with patch.object(CancelamentoViewSet, "get_object", return_value=self._registro()):
            resposta = self.client.get("/api/cancelamento/1/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["data_cancelamento"], "2026-11-10")

    def test_nao_permite_criar_alterar_nem_excluir_cancelamentos(self):
        criar = self.client.post("/api/cancelamento/", {"destino": "descarte"}, format="json")
        alterar = self.client.patch("/api/cancelamento/1/", {"destino": "estoque"}, format="json")
        excluir = self.client.delete("/api/cancelamento/1/")

        for resposta in (criar, alterar, excluir):
            self.assertEqual(resposta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ---------- API: produtos ----------

class ProdutoApiTests(_PedidoApiBase):
    def test_cria_produto_sem_receita(self):
        resposta = self.client.post(
            "/api/produto/", {"nome": "Brigadeiro", "preco_venda": "3.50"}, format="json"
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(resposta.data["receita_nome"])

    def test_cria_produto_com_receita_e_mostra_o_nome_da_receita(self):
        receita = Receita.objects.create(nome="Massa de chocolate")

        resposta = self.client.post(
            "/api/produto/",
            {"nome": "Bolo de chocolate", "preco_venda": "35.00", "receita": receita.id_receita},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["receita_nome"], "Massa de chocolate")

    def test_rejeita_preco_negativo_e_nome_ausente(self):
        negativo = self.client.post("/api/produto/", {"nome": "Torta", "preco_venda": "-1.00"}, format="json")
        sem_nome = self.client.post("/api/produto/", {"preco_venda": "1.00"}, format="json")

        self.assertEqual(negativo.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("preco_venda", negativo.data)
        self.assertEqual(sem_nome.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nome", sem_nome.data)

    def test_lista_os_produtos_em_ordem_alfabetica(self):
        Produto.objects.create(nome="Torta", preco_venda="40.00")
        Produto.objects.create(nome="Bolo", preco_venda="30.00")

        resposta = self.client.get("/api/produto/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        nomes = [produto["nome"] for produto in resposta.data]
        self.assertEqual(nomes, ["Bolo", "Produto de teste", "Torta"])

    def test_rota_no_plural_devolve_a_mesma_listagem(self):
        singular = self.client.get("/api/produto/")
        plural = self.client.get("/api/produtos/")

        self.assertEqual(plural.status_code, status.HTTP_200_OK)
        self.assertEqual(plural.data, singular.data)

    def test_atualiza_o_preco_de_um_produto(self):
        resposta = self.client.patch(
            f"/api/produto/{self.produto.id_produto}/", {"preco_venda": "15.00"}, format="json"
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.preco_venda, Decimal("15.00"))

    def test_exclui_produto_sem_vinculos(self):
        resposta = self.client.delete(f"/api/produto/{self.produto.id_produto}/")

        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Produto.objects.filter(pk=self.produto.pk).exists())

    def test_retorna_nao_encontrado_para_produto_inexistente(self):
        resposta = self.client.get("/api/produto/99999/")

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)


# ---------- API: acesso ----------

class PedidoAcessoApiTests(APITestCase):
    ROTAS = (
        ("get", "/api/pedido/"),
        ("post", "/api/pedido/"),
        ("get", "/api/produto/"),
        ("get", "/api/produtos/"),
        ("get", "/api/cancelamento/"),
        ("post", "/api/pedido/1/consumir-estoque/"),
        ("post", "/api/pedido/1/concluir/"),
        ("post", "/api/pedido/1/cancelar/"),
    )

    @staticmethod
    def _chamar(cliente, metodo, rota):
        funcao = getattr(cliente, metodo)
        if metodo == "get":
            return funcao(rota)
        return funcao(rota, {}, format="json")

    def test_usuario_sem_login_nao_acessa_pedidos_produtos_e_cancelamentos(self):
        for metodo, rota in self.ROTAS:
            with self.subTest(rota=rota, metodo=metodo):
                resposta = self._chamar(APIClient(), metodo, rota)

                self.assertIn(
                    resposta.status_code,
                    (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
                )

    def test_exige_troca_da_senha_inicial_em_todas_as_rotas(self):
        cliente = APIClient()
        cliente.force_authenticate(
            user=SimpleNamespace(is_authenticated=True, primeiro_acesso=True)
        )

        for metodo, rota in self.ROTAS:
            with self.subTest(rota=rota, metodo=metodo):
                resposta = self._chamar(cliente, metodo, rota)

                self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)