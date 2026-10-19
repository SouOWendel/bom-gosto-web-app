from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Ingrediente
from .serializers import IngredienteSerializer
from .views import IngredienteViewSet

# classe que testaa a API do modulo Inventario, garantindo que as operacoes de CRUD funcionem corretamente e que as validacoes sejam aplicadas conforme esperado
class IngredienteApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(
            user=SimpleNamespace(
                is_authenticated=True,
                primeiro_acesso=False
            )
        )

    # metodo auxiliar para atualizar os campos de um objeto Ingrediente com os dados fornecidos, usado nos testes para simular a atualizacao de um ingrediente existente
    @staticmethod
    def atualizar_ingrediente(instance, dados):
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        return instance

    # testa a criacao, consulta, listagem e atualizacao de um ingrediente, verificando se os endpoints da API respondem corretamente e se os dados retornados correspondem ao esperado, incluindo a validacao do campo calculado abaixo_do_minimo
    def test_cria_lista_consulta_e_atualiza_ingrediente(self):
        ingrediente = Ingrediente(
            id_ingrediente=1,
            nome="Farinha",
            quantidade_disponivel=Decimal("4.50"),
            custo_unitario=Decimal("3.25"),
            data_validade="2027-01-31",
            quantidade_minima=Decimal("5.00")
        )
        dados = {
            "nome": "Farinha",
            "quantidade_disponivel": "4.50",
            "custo_unitario": "3.25",
            "data_validade": "2027-01-31",
            "quantidade_minima": "5.00"
        }

        with (
            patch.object(IngredienteSerializer, "create", return_value=ingrediente),
            patch.object(IngredienteViewSet, "get_queryset", return_value=[ingrediente]),
            patch.object(IngredienteViewSet, "get_object", return_value=ingrediente),
            patch.object(
                IngredienteSerializer,
                "update",
                side_effect=self.atualizar_ingrediente,
            ),
        ):
            criacao = self.client.post(
                "/api/inventario/ingrediente/",
                dados,
                format="json",
            )
            consulta = self.client.get("/api/inventario/ingrediente/1/")
            listagem = self.client.get("/api/inventario/ingrediente/")
            atualizacao = self.client.patch(
                "/api/inventario/ingrediente/1/",
                {"quantidade_disponivel": "6.00"},
                format="json",
            )

        self.assertEqual(criacao.status_code, status.HTTP_201_CREATED)
        self.assertEqual(criacao.data["id_ingrediente"], 1)
        self.assertIn("custo_unitario", criacao.data)
        self.assertTrue(criacao.data["abaixo_do_minimo"])
        self.assertEqual(consulta.status_code, status.HTTP_200_OK)
        self.assertEqual(consulta.data["nome"], "Farinha")
        self.assertEqual(listagem.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listagem.data), 1)
        self.assertEqual(atualizacao.status_code, status.HTTP_200_OK)
        self.assertFalse(atualizacao.data["abaixo_do_minimo"])

    # testa que ao atualizar um ingrediente via PUT, os campos opcionais que nao foram fornecidos na requisicao permanecem inalterados, garantindo que a API não sobrescreva dados existentes com valores nulos ou padrao
    def test_put_preserva_campos_opcionais_omitidos(self):
        ingrediente = Ingrediente(
            id_ingrediente=1,
            nome="Chocolate",
            quantidade_disponivel=Decimal("2.00"),
            custo_unitario=Decimal("10.00"),
            quantidade_minima=Decimal("1.00"),
        )

        with (
            patch.object(IngredienteViewSet, "get_object", return_value=ingrediente),
            patch.object(IngredienteSerializer, "update", return_value=ingrediente),
        ):
            resposta = self.client.put(
                "/api/inventario/ingrediente/1/",
                {"nome": "Chocolate em pó"},
                format="json",
            )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["quantidade_disponivel"], "2.00")
        self.assertEqual(resposta.data["custo_unitario"], "10.00")

    # testa que a API rejeita dados invalidos, como uma quantidade disponivel negativa e retorna os erros de validacao apropriados, garantindo que as regras de negocio definidas nos serializers sejam aplicadas corretamente
    def test_rejeita_dados_invalidos(self):
        serializer = IngredienteSerializer(
            data={
                "nome": "Açúcar",
                "quantidade_disponivel": "-1.00",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("quantidade_disponivel", serializer.errors)

    # testa que ao tentar acessar um ingrediente inexistente, a API retorna um status 404 Not Found, garantindo que o tratamento de erros para recursos nao encontrados esteja funcionando corretamente
    def test_retorna_nao_encontrado_para_ingrediente_inexistente(self):
        with patch.object(IngredienteViewSet, "get_object", side_effect=Http404):
            resposta = self.client.get("/api/inventario/ingrediente/999/")

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    # testa que a API nao permite a exclusao de ingredientes, retornando um status 405 Method Not Allowed, garantindo que a operação de DELETE nao esteja habilitada para o endpoint de ingredientes
    def test_nao_disponibiliza_exclusao(self):
        resposta = self.client.delete("/api/inventario/ingrediente/1/")

        self.assertEqual(resposta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # testa que a API exige que o usuario troque a senha inicial no primeiro acesso, retornando um status 403 Forbidden, garantindo que a politica de seguranca para novos usuarios seja aplicada corretamente
    def test_exige_troca_da_senha_inicial(self):
        self.client.force_authenticate(
            user=SimpleNamespace(
                is_authenticated=True,
                primeiro_acesso=True,
            )
        )

        resposta = self.client.get("/api/inventario/ingrediente/")

        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)
