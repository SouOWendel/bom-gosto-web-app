from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.db.models import Q
from django.http import Http404
from django.test import SimpleTestCase
from rest_framework import serializers, status
from rest_framework.test import APIClient

from pedido.models import Produto

from .models import Estoque
from .serializers import EstoqueSerializer
from .views import EstoqueViewSet

# classe que testa a API do modulo Estoque, garantindo que as operacoes de CRUD funcionem corretamente e que as validacoes sejam aplicadas conforme esperado
class EstoqueApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(
            user=SimpleNamespace(
                is_authenticated=True,
                primeiro_acesso=False
            )
        )
        self.produto = Produto(
            id_produto=7,
            nome="Bolo de chocolate",
            preco_venda=Decimal("35.00")
        )
        self.lote = Estoque(
            id_estoque=1,
            produto=self.produto,
            quantidade_disponivel=Decimal("4.00"),
            data_validade=date(2027, 1, 31),
            custo=Decimal("12.50")
        )

    # metodo auxiliar para atualizar os campos de um objeto Estoque com os dados fornecidos, usado nos testes para simular a atualizacao de um lote existente
    @staticmethod
    def atualizar_estoque(instance, dados):
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        return instance

    # testa a criacao, consulta, listagem e atualizacao de um lote, verificando se os endpoints da API respondem corretamente e se os dados retornados correspondem ao esperado, incluindo a validacao do campo calculado vencido
    def test_cria_lista_consulta_e_atualiza_lote(self):
        dados = {
            "id_produto": self.produto.id_produto,
            "quantidade_disponivel": "4.00",
            "data_validade": "2027-01-31",
            "custo": "12.50"
        }

        with (
            patch.object(
                serializers.PrimaryKeyRelatedField,
                "to_internal_value",
                return_value=self.produto
            ),
            patch.object(EstoqueSerializer, "create", return_value=self.lote),
            patch.object(EstoqueViewSet, "get_queryset", return_value=[self.lote]),
            patch.object(EstoqueViewSet, "get_object", return_value=self.lote),
            patch.object(
                EstoqueSerializer,
                "update",
                side_effect=self.atualizar_estoque
            ),
        ):
            criacao = self.client.post("/api/estoque/", dados, format="json")
            consulta = self.client.get("/api/estoque/1/")
            listagem = self.client.get("/api/estoque/")
            atualizacao = self.client.patch(
                "/api/estoque/1/",
                {"quantidade_disponivel": "6.00"},
                format="json"
            )

        self.assertEqual(criacao.status_code, status.HTTP_201_CREATED)
        self.assertEqual(criacao.data["id_produto"], 7)
        self.assertEqual(criacao.data["quantidade_disponivel"], "4.00")
        self.assertFalse(criacao.data["vencido"])
        self.assertEqual(consulta.status_code, status.HTTP_200_OK)
        self.assertEqual(listagem.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listagem.data), 1)
        self.assertEqual(atualizacao.status_code, status.HTTP_200_OK)
        self.assertEqual(atualizacao.data["quantidade_disponivel"], "6.00")

    # testa se a validacao de quantidade disponivel e custo negativo funciona corretamente, garantindo que o serializer rejeite valores invalidos e lance a excecao apropriada
    def test_rejeita_quantidades_e_custos_negativos(self):
        serializer = EstoqueSerializer()

        with self.assertRaises(serializers.ValidationError):
            serializer.validate_quantidade_disponivel(Decimal("-1.00"))
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_custo(Decimal("-0.01"))

    # testa se o campo vencido é calculado corretamente com base na data de validade do lote, garantindo que o serializer retorne True para lotes vencidos e False para lotes ainda validos
    def test_indica_lote_vencido(self):
        vencido = Estoque(data_validade=date(2020, 1, 1))
        serializer = EstoqueSerializer()

        with patch(
            "estoque.serializers.timezone.localdate",
            return_value=date(2026, 1, 1)
        ):
            self.assertTrue(serializer.get_vencido(vencido))
            self.assertFalse(serializer.get_vencido(self.lote))

    # testa a consulta de disponibilidade de produto e o encaminhamento para producao, verificando se a API retorna corretamente os dados de saldo e se indica quando encaminhar para producao
    def test_consulta_disponibilidade_e_encaminhamento_para_producao(self):
        with (
            patch.object(
                serializers.PrimaryKeyRelatedField,
                "to_internal_value",
                return_value=self.produto
            ),
            patch(
                "estoque.views.Estoque.objects.verificar_disponibilidade",
                return_value={
                    "quantidade_solicitada": Decimal("3.00"),
                    "quantidade_disponivel": Decimal("4.00"),
                    "disponivel": True,
                    "encaminhar_para_producao": False
                },
            ) as verificar
        ):
            resposta = self.client.get(
                "/api/estoque/disponibilidade/",
                {"id_produto": 7, "quantidade": "3.00"}
            )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.data["disponivel"])
        self.assertFalse(resposta.data["encaminhar_para_producao"])
        verificar.assert_called_once_with(7, Decimal("3.00"))

        with (
            patch.object(
                serializers.PrimaryKeyRelatedField,
                "to_internal_value",
                return_value=self.produto
            ),
            patch(
                "estoque.views.Estoque.objects.verificar_disponibilidade",
                return_value={
                    "quantidade_solicitada": Decimal("3.00"),
                    "quantidade_disponivel": Decimal("2.00"),
                    "disponivel": False,
                    "encaminhar_para_producao": True
                }
            )
        ):
            resposta = self.client.get(
                "/api/estoque/disponibilidade/",
                {"id_produto": 7, "quantidade": "3.00"}
            )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertFalse(resposta.data["disponivel"])
        self.assertTrue(resposta.data["encaminhar_para_producao"])

    # testa se a API rejeita uma quantidade solicitada invalida (menor ou igual a zero), garantindo que o endpoint de disponibilidade retorne um erro 400 Bad Request quando a quantidade nao for positiva
    def test_rejeita_quantidade_solicitada_invalida(self):
        with patch.object(
            serializers.PrimaryKeyRelatedField,
            "to_internal_value",
            return_value=self.produto
        ):
            resposta = self.client.get(
                "/api/estoque/disponibilidade/",
                {"id_produto": 7, "quantidade": "0"}
            )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    # testa se a API retorna um status 404 Not Found ao tentar acessar um lote inexistente, garantindo que o tratamento de erros para recursos nao encontrados esteja funcionando corretamente
    def test_retorna_nao_encontrado_para_lote_inexistente(self):
        with patch.object(EstoqueViewSet, "get_object", side_effect=Http404):
            resposta = self.client.get("/api/estoque/999/")

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    # testa se a API nao permite a exclusao de lotes, garantindo que o endpoint DELETE retorne um status 405 Method Not Allowed, pois a exclusao de lotes nao é suportada
    def test_nao_disponibiliza_exclusao(self):
        resposta = self.client.delete("/api/estoque/1/")

        self.assertEqual(resposta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # testa se a API exige que o usuario troque a senha inicial no primeiro acesso, garantindo que o endpoint retorne um status 403 Forbidden quando o usuario estiver no estado de primeiro acesso
    def test_exige_troca_da_senha_inicial(self):
        self.client.force_authenticate(
            user=SimpleNamespace(
                is_authenticated=True,
                primeiro_acesso=True
            )
        )

        resposta = self.client.get("/api/estoque/")

        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

# classe que testa o metodo de verificacao de disponibilidade do EstoqueManager, garantindo que a logica de consulta de saldo e encaminhamento para producao funcione corretamente com base nos dados simulados
class EstoqueManagerTests(SimpleTestCase):

    # testa a verificacao de disponibilidade de produto e o encaminhamento para producao, simulando a consulta ao banco de dados e verificando se o metodo retorna os valores corretos de saldo e indicacao de producao
    def test_verifica_saldo_valido_e_encaminhamento_para_producao(self):
        with (
            patch(
                "estoque.models.timezone.localdate",
                return_value=date(2026, 1, 1)
            ),
            patch("estoque.models.EstoqueManager.filter") as filtrar
        ):
            filtrar.return_value.filter.return_value.aggregate.return_value = {
                "total": Decimal("2.00")
            }
            resultado = Estoque.objects.verificar_disponibilidade(
                7,
                Decimal("3.00")
            )

        filtrar.assert_called_once_with(produto_id=7)
        filtrar.return_value.filter.assert_called_once_with(
            Q(data_validade__isnull=True) | Q(data_validade__gte=date(2026, 1, 1))
        )
        self.assertEqual(resultado["quantidade_disponivel"], Decimal("2.00"))
        self.assertFalse(resultado["disponivel"])
        self.assertTrue(resultado["encaminhar_para_producao"])
