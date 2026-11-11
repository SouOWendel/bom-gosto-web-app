from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Ingrediente
from .serializers import IngredienteSerializer
from .views import IngredienteViewSet

# classe que testaa a API do modulo Inventario, garantindo que as operacoes de CRUD funcionem corretamente e que as validacoes sejam aplicadas conforme esperado
class IngredienteApiTests(APITestCase):
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
            data_validade=date(2027, 1, 31),
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
        self.assertEqual(atualizacao.data["data_validade"], "2027-01-31")

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

    def test_movimenta_entrada_e_saida_sem_permitir_saldo_negativo(self):
        ingrediente = Ingrediente(
            id_ingrediente=1,
            nome="Farinha",
            quantidade_disponivel=Decimal("4.00"),
        )

        with patch.object(IngredienteViewSet, "get_object", return_value=ingrediente):
            with patch.object(ingrediente, "save") as salvar:
                entrada = self.client.post(
                    "/api/inventario/ingrediente/1/movimentar/",
                    {
                        "tipo": "entrada",
                        "quantidade": "2.50",
                        "custo_unitario": "3.25",
                        "data_validade": "2027-01-31",
                    },
                    format="json",
                )
                self.assertEqual(entrada.status_code, status.HTTP_200_OK)
                self.assertEqual(ingrediente.quantidade_disponivel, Decimal("6.50"))
                self.assertEqual(ingrediente.custo_unitario, Decimal("3.25"))
                self.assertEqual(ingrediente.data_validade, date(2027, 1, 31))

                saida = self.client.post(
                    "/api/inventario/ingrediente/1/movimentar/",
                    {"tipo": "saida", "quantidade": "1.50"},
                    format="json",
                )
                self.assertEqual(saida.status_code, status.HTTP_200_OK)
                self.assertEqual(ingrediente.quantidade_disponivel, Decimal("5.00"))
                self.assertGreaterEqual(salvar.call_count, 2)

                negativa = self.client.post(
                    "/api/inventario/ingrediente/1/movimentar/",
                    {"tipo": "saida", "quantidade": "6.00"},
                    format="json",
                )

        self.assertEqual(negativa.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantidade", negativa.data)

    def test_classifica_alertas_de_validade(self):
        serializer = IngredienteSerializer()
        hoje = date(2026, 1, 1)
        with patch("inventario.serializers.timezone.localdate", return_value=hoje):
            self.assertEqual(serializer.get_alerta_validade(Ingrediente(data_validade=hoje))["nivel"], "critico")
            self.assertEqual(serializer.get_alerta_validade(Ingrediente(data_validade=hoje + timedelta(days=7)))["nivel"], "atencao")
            self.assertEqual(serializer.get_alerta_validade(Ingrediente(data_validade=hoje + timedelta(days=15)))["nivel"], "preventivo")

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

# testes complementares do modulo Inventario: validacoes do serializer e campos calculados
class IngredienteSerializerTests(SimpleTestCase):
    def test_aceita_ingrediente_apenas_com_nome(self):
        serializer = IngredienteSerializer(data={"nome": "Sal"})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_exige_nome(self):
        serializer = IngredienteSerializer(data={"quantidade_disponivel": "1.00"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("nome", serializer.errors)

    def test_rejeita_nome_maior_que_cem_caracteres(self):
        serializer = IngredienteSerializer(data={"nome": "a" * 101})

        self.assertFalse(serializer.is_valid())
        self.assertIn("nome", serializer.errors)

    def test_rejeita_custo_unitario_negativo(self):
        serializer = IngredienteSerializer(
            data={"nome": "Açúcar", "custo_unitario": "-0.01"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("custo_unitario", serializer.errors)

    def test_rejeita_quantidade_minima_negativa(self):
        serializer = IngredienteSerializer(
            data={"nome": "Açúcar", "quantidade_minima": "-1.00"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("quantidade_minima", serializer.errors)

    def test_aceita_valores_zerados(self):
        serializer = IngredienteSerializer(
            data={
                "nome": "Sal",
                "quantidade_disponivel": "0.00",
                "custo_unitario": "0.00",
                "quantidade_minima": "0.00",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_abaixo_do_minimo_compara_saldo_e_minimo(self):
        serializer = IngredienteSerializer()
        abaixo = Ingrediente(
            quantidade_disponivel=Decimal("4.99"), quantidade_minima=Decimal("5.00")
        )
        igual = Ingrediente(
            quantidade_disponivel=Decimal("5.00"), quantidade_minima=Decimal("5.00")
        )
        acima = Ingrediente(
            quantidade_disponivel=Decimal("6.00"), quantidade_minima=Decimal("5.00")
        )

        self.assertIs(serializer.get_abaixo_do_minimo(abaixo), True)
        self.assertIs(serializer.get_abaixo_do_minimo(igual), False)
        self.assertIs(serializer.get_abaixo_do_minimo(acima), False)

    def test_abaixo_do_minimo_e_nulo_sem_saldo_ou_sem_minimo(self):
        serializer = IngredienteSerializer()
        sem_saldo = Ingrediente(quantidade_minima=Decimal("5.00"))
        sem_minimo = Ingrediente(quantidade_disponivel=Decimal("1.00"))

        self.assertIsNone(serializer.get_abaixo_do_minimo(sem_saldo))
        self.assertIsNone(serializer.get_abaixo_do_minimo(sem_minimo))

    def test_alerta_de_validade_nas_fronteiras_das_faixas(self):
        serializer = IngredienteSerializer()
        hoje = date(2026, 1, 1)
        casos = [
            (-3, "critico"),
            (0, "critico"),
            (1, "atencao"),
            (7, "atencao"),
            (8, "preventivo"),
            (15, "preventivo"),
            (16, None),
        ]

        with patch("inventario.serializers.timezone.localdate", return_value=hoje):
            for dias, nivel in casos:
                with self.subTest(dias=dias):
                    alerta = serializer.get_alerta_validade(
                        Ingrediente(data_validade=hoje + timedelta(days=dias))
                    )
                    if nivel is None:
                        self.assertIsNone(alerta)
                    else:
                        self.assertEqual(alerta["nivel"], nivel)
                        self.assertEqual(alerta["dias_para_vencer"], dias)

    def test_sem_data_de_validade_nao_ha_alerta(self):
        serializer = IngredienteSerializer()

        self.assertIsNone(serializer.get_alerta_validade(Ingrediente()))


# testes complementares da acao /movimentar/ (entrada e saida de saldo)
class IngredienteMovimentacaoApiTests(APITestCase):
    URL = "/api/inventario/ingrediente/1/movimentar/"
    CAMPOS_SALVOS = ["quantidade_disponivel", "custo_unitario", "data_validade"]

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(
            user=SimpleNamespace(is_authenticated=True, primeiro_acesso=False)
        )

    # metodo auxiliar que envia a movimentacao sem acessar o banco (get_object e save simulados)
    def _movimentar(self, ingrediente, dados):
        with (
            patch.object(IngredienteViewSet, "get_object", return_value=ingrediente),
            patch.object(ingrediente, "save") as salvar,
        ):
            resposta = self.client.post(self.URL, dados, format="json")
        return resposta, salvar

    @staticmethod
    def _ingrediente(saldo="4.00", **extras):
        valor = None if saldo is None else Decimal(saldo)
        return Ingrediente(id_ingrediente=1, nome="Farinha", quantidade_disponivel=valor, **extras)

    def test_entrada_soma_ao_saldo_e_salva_somente_os_campos_esperados(self):
        ingrediente = self._ingrediente("4.00")

        resposta, salvar = self._movimentar(
            ingrediente, {"tipo": "entrada", "quantidade": "2.50"}
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["quantidade_disponivel"], "6.50")
        salvar.assert_called_once_with(update_fields=self.CAMPOS_SALVOS)

    def test_entrada_sem_custo_e_validade_preserva_os_valores_atuais(self):
        ingrediente = self._ingrediente(
            "4.00", custo_unitario=Decimal("3.00"), data_validade=date(2027, 1, 31)
        )

        resposta, _ = self._movimentar(
            ingrediente, {"tipo": "entrada", "quantidade": "1.00"}
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(ingrediente.custo_unitario, Decimal("3.00"))
        self.assertEqual(ingrediente.data_validade, date(2027, 1, 31))

    def test_entrada_em_ingrediente_sem_saldo_registrado(self):
        ingrediente = self._ingrediente(saldo=None)

        resposta, _ = self._movimentar(
            ingrediente, {"tipo": "entrada", "quantidade": "2.00"}
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(ingrediente.quantidade_disponivel, Decimal("2.00"))

    def test_entrada_com_custo_e_validade_vazios_limpa_os_campos(self):
        ingrediente = self._ingrediente(
            "4.00", custo_unitario=Decimal("3.00"), data_validade=date(2027, 1, 31)
        )

        resposta, _ = self._movimentar(
            ingrediente,
            {
                "tipo": "entrada",
                "quantidade": "1.00",
                "custo_unitario": "",
                "data_validade": "",
            },
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIsNone(ingrediente.custo_unitario)
        self.assertIsNone(ingrediente.data_validade)

    def test_entrada_rejeita_custo_negativo(self):
        ingrediente = self._ingrediente("4.00")

        resposta, salvar = self._movimentar(
            ingrediente,
            {"tipo": "entrada", "quantidade": "1.00", "custo_unitario": "-1.00"},
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("custo_unitario", resposta.data)
        salvar.assert_not_called()

    def test_entrada_rejeita_custo_que_nao_e_numero(self):
        ingrediente = self._ingrediente("4.00")

        resposta, salvar = self._movimentar(
            ingrediente,
            {"tipo": "entrada", "quantidade": "1.00", "custo_unitario": "abc"},
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("custo_unitario", resposta.data)
        salvar.assert_not_called()

    def test_entrada_rejeita_data_de_validade_invalida(self):
        ingrediente = self._ingrediente("4.00")

        resposta, salvar = self._movimentar(
            ingrediente,
            {"tipo": "entrada", "quantidade": "1.00", "data_validade": "31/01/2027"},
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("data_validade", resposta.data)
        salvar.assert_not_called()

    def test_saida_igual_ao_saldo_zera_o_estoque(self):
        ingrediente = self._ingrediente("4.00")

        resposta, _ = self._movimentar(
            ingrediente, {"tipo": "saida", "quantidade": "4.00"}
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(ingrediente.quantidade_disponivel, Decimal("0.00"))

    def test_saida_sem_saldo_registrado_e_rejeitada(self):
        ingrediente = self._ingrediente(saldo=None)

        resposta, salvar = self._movimentar(
            ingrediente, {"tipo": "saida", "quantidade": "1.00"}
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantidade", resposta.data)
        salvar.assert_not_called()

    def test_saida_maior_que_o_saldo_nao_altera_o_estoque(self):
        ingrediente = self._ingrediente("4.00")

        resposta, salvar = self._movimentar(
            ingrediente, {"tipo": "saida", "quantidade": "4.01"}
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ingrediente.quantidade_disponivel, Decimal("4.00"))
        salvar.assert_not_called()

    def test_saida_ignora_custo_e_validade_enviados(self):
        ingrediente = self._ingrediente(
            "4.00", custo_unitario=Decimal("3.00"), data_validade=date(2027, 1, 31)
        )

        resposta, _ = self._movimentar(
            ingrediente,
            {
                "tipo": "saida",
                "quantidade": "1.00",
                "custo_unitario": "99.00",
                "data_validade": "2030-12-31",
            },
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(ingrediente.custo_unitario, Decimal("3.00"))
        self.assertEqual(ingrediente.data_validade, date(2027, 1, 31))

    def test_rejeita_quantidade_invalida_zero_ou_negativa(self):
        for quantidade in ("", "abc", "0", "0.00", "-1.00"):
            with self.subTest(quantidade=quantidade):
                ingrediente = self._ingrediente("4.00")

                resposta, salvar = self._movimentar(
                    ingrediente, {"tipo": "entrada", "quantidade": quantidade}
                )

                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("quantidade", resposta.data)
                self.assertEqual(ingrediente.quantidade_disponivel, Decimal("4.00"))
                salvar.assert_not_called()

    def test_rejeita_quantidade_ausente(self):
        ingrediente = self._ingrediente("4.00")

        resposta, salvar = self._movimentar(ingrediente, {"tipo": "entrada"})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantidade", resposta.data)
        salvar.assert_not_called()

    def test_rejeita_tipo_invalido_ou_ausente(self):
        for dados in (
            {"tipo": "ajuste", "quantidade": "1.00"},
            {"quantidade": "1.00"},
        ):
            with self.subTest(dados=dados):
                ingrediente = self._ingrediente("4.00")

                resposta, salvar = self._movimentar(ingrediente, dados)

                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("tipo", resposta.data)
                salvar.assert_not_called()

    def test_retorna_nao_encontrado_para_ingrediente_inexistente(self):
        with patch.object(IngredienteViewSet, "get_object", side_effect=Http404):
            resposta = self.client.post(
                "/api/inventario/ingrediente/999/movimentar/",
                {"tipo": "entrada", "quantidade": "1.00"},
                format="json",
            )

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)


# testes complementares de acesso e de metodos aceitos pela API de ingredientes
class IngredienteAcessoApiTests(APITestCase):
    def test_usuario_sem_login_nao_acessa_a_listagem(self):
        resposta = APIClient().get("/api/inventario/ingrediente/")

        self.assertIn(
            resposta.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_usuario_sem_login_nao_movimenta_estoque(self):
        resposta = APIClient().post(
            "/api/inventario/ingrediente/1/movimentar/",
            {"tipo": "entrada", "quantidade": "1.00"},
            format="json",
        )

        self.assertIn(
            resposta.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_movimentar_exige_troca_da_senha_inicial(self):
        cliente = APIClient()
        cliente.force_authenticate(
            user=SimpleNamespace(is_authenticated=True, primeiro_acesso=True)
        )

        resposta = cliente.post(
            "/api/inventario/ingrediente/1/movimentar/",
            {"tipo": "entrada", "quantidade": "1.00"},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_movimentar_aceita_apenas_post(self):
        cliente = APIClient()
        cliente.force_authenticate(
            user=SimpleNamespace(is_authenticated=True, primeiro_acesso=False)
        )

        resposta = cliente.get("/api/inventario/ingrediente/1/movimentar/")

        self.assertEqual(resposta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cadastro_sem_nome_retorna_erro_de_validacao(self):
        cliente = APIClient()
        cliente.force_authenticate(
            user=SimpleNamespace(is_authenticated=True, primeiro_acesso=False)
        )

        resposta = cliente.post(
            "/api/inventario/ingrediente/",
            {"quantidade_disponivel": "1.00"},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nome", resposta.data)