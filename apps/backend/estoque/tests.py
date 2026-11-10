from datetime import date, timedelta
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

    # Cadastro de lote fica restrito aos fluxos automáticos de produção e cancelamento.
    def test_lista_consulta_atualiza_lote_e_bloqueia_cadastro_manual(self):
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

        self.assertEqual(criacao.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
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

    def test_classifica_alertas_de_validade(self):
        serializer = EstoqueSerializer()
        hoje = date(2026, 1, 1)
        with patch("estoque.serializers.timezone.localdate", return_value=hoje):
            self.assertEqual(serializer.get_alerta_validade(Estoque(data_validade=hoje))["nivel"], "critico")
            self.assertEqual(serializer.get_alerta_validade(Estoque(data_validade=hoje + timedelta(days=7)))["nivel"], "atencao")
            self.assertEqual(serializer.get_alerta_validade(Estoque(data_validade=hoje + timedelta(days=15)))["nivel"], "preventivo")

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

# imports adicionais usados pelos testes complementares abaixo
from contextlib import ExitStack, contextmanager
from unittest.mock import Mock
from django.db.models import PROTECT, ProtectedError, QuerySet
from django.db.transaction import Atomic
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase
from django.test import TestCase
from django.utils import timezone
from .models import EstoqueManager
from .serializers import VerificarDisponibilidadeSerializer
from .services import baixar_lotes


# testes complementares do modulo Estoque (servico de baixa de lotes, disponibilidade, serializers e API)
# usam objetos simulados, como os testes ja existentes em tests.py, para nao depender do banco


# ---------- apoio ----------

def _produto():
    return Produto(id_produto=7, nome="Bolo de chocolate", preco_venda=Decimal("35.00"))


def _lote(**extras):
    dados = {
        "id_estoque": 1,
        "produto": _produto(),
        "quantidade_disponivel": Decimal("4.00"),
        "data_validade": date(2027, 1, 31),
        "custo": Decimal("12.50"),
    }
    dados.update(extras)
    return Estoque(**dados)


def _lote_falso(saldo):
    return SimpleNamespace(quantidade_disponivel=Decimal(saldo), save=Mock())


def _usuario(primeiro_acesso=False):
    return SimpleNamespace(is_authenticated=True, primeiro_acesso=primeiro_acesso)


# evita abrir transacao real e simula a consulta de lotes ordenados por validade
@contextmanager
def _ambiente_baixa(lotes):
    with ExitStack() as pilha:
        pilha.enter_context(patch.object(Atomic, "__enter__", return_value=None))
        pilha.enter_context(patch.object(Atomic, "__exit__", return_value=False))
        pilha.enter_context(patch("estoque.services.timezone.localdate", return_value=date(2026, 1, 1)))
        bloqueio = pilha.enter_context(patch("estoque.services.Estoque.objects.select_for_update"))
        primeiro_filtro = bloqueio.return_value.filter
        segundo_filtro = primeiro_filtro.return_value.filter
        segundo_filtro.return_value.order_by.return_value = lotes
        yield SimpleNamespace(
            bloqueio=bloqueio,
            primeiro_filtro=primeiro_filtro,
            segundo_filtro=segundo_filtro,
            ordenacao=segundo_filtro.return_value.order_by,
        )


# ---------- baixar_lotes ----------

class BaixarLotesTests(SimpleTestCase):
    def test_consome_primeiro_o_lote_de_validade_mais_proxima(self):
        proximo, distante = _lote_falso("3.00"), _lote_falso("5.00")

        with _ambiente_baixa([proximo, distante]):
            baixar_lotes(7, 2)

        self.assertEqual(proximo.quantidade_disponivel, Decimal("1.00"))
        self.assertEqual(distante.quantidade_disponivel, Decimal("5.00"))
        proximo.save.assert_called_once_with(update_fields=["quantidade_disponivel"])
        distante.save.assert_not_called()

    def test_consulta_lotes_do_produto_bloqueados_e_ordenados_por_validade(self):
        with _ambiente_baixa([_lote_falso("3.00")]) as amb:
            baixar_lotes(7, 1)

        amb.bloqueio.assert_called_once_with()
        amb.primeiro_filtro.assert_called_once_with(produto_id=7)
        amb.ordenacao.assert_called_once_with("data_validade", "id_estoque")

    def test_considera_apenas_lotes_sem_validade_ou_ainda_validos(self):
        with _ambiente_baixa([_lote_falso("3.00")]) as amb:
            baixar_lotes(7, 1)

        amb.segundo_filtro.assert_called_once_with(
            Q(data_validade__isnull=True) | Q(data_validade__gte=date(2026, 1, 1))
        )

    def test_completa_a_baixa_com_o_proximo_lote_quando_o_primeiro_nao_basta(self):
        primeiro, segundo = _lote_falso("3.00"), _lote_falso("5.00")

        with _ambiente_baixa([primeiro, segundo]):
            baixar_lotes(7, 4)

        self.assertEqual(primeiro.quantidade_disponivel, Decimal("0.00"))
        self.assertEqual(segundo.quantidade_disponivel, Decimal("4.00"))
        primeiro.save.assert_called_once_with(update_fields=["quantidade_disponivel"])
        segundo.save.assert_called_once_with(update_fields=["quantidade_disponivel"])

    def test_zera_os_lotes_quando_a_quantidade_e_igual_ao_saldo_total(self):
        primeiro, segundo = _lote_falso("3.00"), _lote_falso("2.00")

        with _ambiente_baixa([primeiro, segundo]):
            baixar_lotes(7, 5)

        self.assertEqual(primeiro.quantidade_disponivel, Decimal("0.00"))
        self.assertEqual(segundo.quantidade_disponivel, Decimal("0.00"))

    def test_interrompe_a_baixa_assim_que_a_quantidade_e_atendida(self):
        primeiro, segundo = _lote_falso("3.00"), _lote_falso("5.00")

        with _ambiente_baixa([primeiro, segundo]):
            baixar_lotes(7, 3)

        segundo.save.assert_not_called()
        self.assertEqual(segundo.quantidade_disponivel, Decimal("5.00"))

    def test_rejeita_quando_o_saldo_valido_nao_e_suficiente(self):
        lote = _lote_falso("3.00")

        with _ambiente_baixa([lote]):
            with self.assertRaises(ValidationError) as erro:
                baixar_lotes(7, 4)

        self.assertIn("estoque", erro.exception.detail)

    def test_rejeita_quando_nao_ha_nenhum_lote_valido(self):
        with _ambiente_baixa([]):
            with self.assertRaises(ValidationError) as erro:
                baixar_lotes(7, 1)

        self.assertIn("estoque", erro.exception.detail)

    def test_lote_sem_saldo_e_ignorado_sem_ser_gravado(self):
        vazio, com_saldo = _lote_falso("0.00"), _lote_falso("5.00")

        with _ambiente_baixa([vazio, com_saldo]):
            baixar_lotes(7, 2)

        vazio.save.assert_not_called()
        self.assertEqual(com_saldo.quantidade_disponivel, Decimal("3.00"))

    def test_aceita_quantidade_em_inteiro_texto_ou_decimal(self):
        for quantidade, esperado in ((2, Decimal("3.00")), ("2.00", Decimal("3.00")), (Decimal("1.50"), Decimal("3.50"))):
            with self.subTest(quantidade=quantidade):
                lote = _lote_falso("5.00")

                with _ambiente_baixa([lote]):
                    baixar_lotes(7, quantidade)

                self.assertEqual(lote.quantidade_disponivel, esperado)


# ---------- EstoqueManager.verificar_disponibilidade ----------

class VerificarDisponibilidadeManagerTests(SimpleTestCase):
    # metodo auxiliar que simula o saldo valido somado pelo banco e devolve o resultado da verificacao
    @staticmethod
    def _verificar(saldo, quantidade):
        with (
            patch("estoque.models.timezone.localdate", return_value=date(2026, 1, 1)),
            patch("estoque.models.EstoqueManager.filter") as filtrar,
        ):
            filtrar.return_value.filter.return_value.aggregate.return_value = {"total": saldo}
            return Estoque.objects.verificar_disponibilidade(7, quantidade)

    def test_saldo_igual_a_quantidade_solicitada_esta_disponivel(self):
        resultado = self._verificar(Decimal("3.00"), Decimal("3.00"))

        self.assertTrue(resultado["disponivel"])
        self.assertFalse(resultado["encaminhar_para_producao"])

    def test_saldo_maior_que_a_quantidade_solicitada_esta_disponivel(self):
        resultado = self._verificar(Decimal("10.00"), Decimal("3.00"))

        self.assertTrue(resultado["disponivel"])
        self.assertEqual(resultado["quantidade_disponivel"], Decimal("10.00"))

    def test_sem_lotes_validos_o_saldo_e_zero_e_segue_para_producao(self):
        resultado = self._verificar(None, Decimal("1.00"))

        self.assertEqual(resultado["quantidade_disponivel"], Decimal("0.00"))
        self.assertFalse(resultado["disponivel"])
        self.assertTrue(resultado["encaminhar_para_producao"])

    def test_devolve_a_quantidade_solicitada_sem_alteracao(self):
        resultado = self._verificar(Decimal("2.00"), Decimal("3.50"))

        self.assertEqual(resultado["quantidade_solicitada"], Decimal("3.50"))

    def test_soma_o_saldo_dos_lotes_com_agregacao_total(self):
        with (
            patch("estoque.models.timezone.localdate", return_value=date(2026, 1, 1)),
            patch("estoque.models.EstoqueManager.filter") as filtrar,
        ):
            agregar = filtrar.return_value.filter.return_value.aggregate
            agregar.return_value = {"total": Decimal("2.00")}
            Estoque.objects.verificar_disponibilidade(7, Decimal("1.00"))

        self.assertEqual(list(agregar.call_args.kwargs), ["total"])


class EstoqueModelTests(SimpleTestCase):
    def test_usa_o_manager_com_verificacao_de_disponibilidade(self):
        self.assertIsInstance(Estoque.objects, EstoqueManager)

    def test_tabela_do_estoque(self):
        self.assertEqual(Estoque._meta.db_table, "estoque")

    def test_produto_com_lotes_nao_pode_ser_excluido(self):
        self.assertIs(Estoque._meta.get_field("produto").remote_field.on_delete, PROTECT)


# ---------- EstoqueSerializer ----------

class EstoqueSerializerRegrasTests(SimpleTestCase):
    def test_quantidade_disponivel_aceita_zero_e_valores_positivos(self):
        serializer = EstoqueSerializer()

        self.assertEqual(serializer.validate_quantidade_disponivel(Decimal("0")), Decimal("0"))
        self.assertEqual(serializer.validate_quantidade_disponivel(Decimal("2.50")), Decimal("2.50"))

    def test_custo_aceita_nulo_zero_e_valores_positivos(self):
        serializer = EstoqueSerializer()

        self.assertIsNone(serializer.validate_custo(None))
        self.assertEqual(serializer.validate_custo(Decimal("0")), Decimal("0"))
        self.assertEqual(serializer.validate_custo(Decimal("9.90")), Decimal("9.90"))

    def test_lote_so_esta_vencido_depois_da_data_de_validade(self):
        serializer = EstoqueSerializer()
        hoje = date(2026, 1, 1)
        casos = (
            (hoje - timedelta(days=1), True),
            (hoje, False),
            (hoje + timedelta(days=1), False),
            (None, False),
        )

        with patch("estoque.serializers.timezone.localdate", return_value=hoje):
            for validade, esperado in casos:
                with self.subTest(validade=validade):
                    self.assertIs(bool(serializer.get_vencido(Estoque(data_validade=validade))), esperado)

    def test_alerta_de_validade_nas_fronteiras_das_faixas(self):
        serializer = EstoqueSerializer()
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

        with patch("estoque.serializers.timezone.localdate", return_value=hoje):
            for dias, nivel in casos:
                with self.subTest(dias=dias):
                    alerta = serializer.get_alerta_validade(
                        Estoque(data_validade=hoje + timedelta(days=dias))
                    )
                    if nivel is None:
                        self.assertIsNone(alerta)
                    else:
                        self.assertEqual(alerta["nivel"], nivel)
                        self.assertEqual(alerta["dias_para_vencer"], dias)

    def test_sem_data_de_validade_nao_ha_alerta(self):
        self.assertIsNone(EstoqueSerializer().get_alerta_validade(Estoque()))

    def test_serializa_dados_do_produto_e_campos_calculados(self):
        lote = _lote(data_validade=date(2026, 1, 4))

        with patch("estoque.serializers.timezone.localdate", return_value=date(2026, 1, 1)):
            dados = EstoqueSerializer(lote).data

        self.assertEqual(dados["id_produto"], 7)
        self.assertEqual(dados["produto_nome"], "Bolo de chocolate")
        self.assertEqual(dados["produto_preco_venda"], "35.00")
        self.assertEqual(dados["quantidade_disponivel"], "4.00")
        self.assertEqual(dados["custo"], "12.50")
        self.assertFalse(dados["vencido"])
        self.assertEqual(dados["alerta_validade"], {"nivel": "atencao", "dias_para_vencer": 3})


# ---------- VerificarDisponibilidadeSerializer ----------

class VerificarDisponibilidadeSerializerTests(SimpleTestCase):
    def test_quantidade_deve_ser_maior_que_zero(self):
        serializer = VerificarDisponibilidadeSerializer()

        for valor in (Decimal("0.00"), Decimal("-1.00")):
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    serializer.validate_quantidade(valor)
        self.assertEqual(serializer.validate_quantidade(Decimal("0.01")), Decimal("0.01"))

    def test_campo_quantidade_rejeita_texto_virgula_e_mais_de_duas_casas(self):
        campo = VerificarDisponibilidadeSerializer().fields["quantidade"]

        for valor in ("abc", "3,5", "1.234"):
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    campo.run_validation(valor)
        self.assertEqual(campo.run_validation("3.50"), Decimal("3.50"))

    def test_exige_produto_e_quantidade(self):
        serializer = VerificarDisponibilidadeSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("id_produto", serializer.errors)
        self.assertIn("quantidade", serializer.errors)

    def test_aceita_produto_existente_e_quantidade_valida(self):
        produto = _produto()
        with patch.object(serializers.PrimaryKeyRelatedField, "to_internal_value", return_value=produto):
            serializer = VerificarDisponibilidadeSerializer(data={"id_produto": "7", "quantidade": "3.00"})

            self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertEqual(serializer.validated_data["produto"], produto)
        self.assertEqual(serializer.validated_data["quantidade"], Decimal("3.00"))

    def test_rejeita_produto_inexistente(self):
        with patch.object(QuerySet, "get", side_effect=Produto.DoesNotExist):
            serializer = VerificarDisponibilidadeSerializer(data={"id_produto": 999, "quantidade": "1.00"})

            self.assertFalse(serializer.is_valid())

        self.assertIn("id_produto", serializer.errors)


# ---------- API: lotes e disponibilidade ----------

class EstoqueApiRegrasTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=_usuario())
        self.produto = _produto()
        self.lote = _lote(produto=self.produto)

    @staticmethod
    def _atualizar(instance, dados):
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        return instance

    def test_listagem_inclui_dados_do_produto_e_alertas_calculados(self):
        lote = _lote(data_validade=date(2026, 1, 4))
        with (
            patch.object(EstoqueViewSet, "get_queryset", return_value=[lote]),
            patch("estoque.serializers.timezone.localdate", return_value=date(2026, 1, 1)),
        ):
            resposta = self.client.get("/api/estoque/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        item = resposta.data[0]
        self.assertEqual(item["produto_nome"], "Bolo de chocolate")
        self.assertEqual(item["produto_preco_venda"], "35.00")
        self.assertFalse(item["vencido"])
        self.assertEqual(item["alerta_validade"]["nivel"], "atencao")

    def test_put_atualiza_o_lote_completo(self):
        dados = {
            "id_produto": 7,
            "quantidade_disponivel": "8.00",
            "data_validade": "2027-02-28",
            "custo": "9.90",
        }
        with (
            patch.object(serializers.PrimaryKeyRelatedField, "to_internal_value", return_value=self.produto),
            patch.object(EstoqueViewSet, "get_object", return_value=self.lote),
            patch.object(EstoqueSerializer, "update", side_effect=self._atualizar),
        ):
            resposta = self.client.put("/api/estoque/1/", dados, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["quantidade_disponivel"], "8.00")
        self.assertEqual(resposta.data["data_validade"], "2027-02-28")
        self.assertEqual(resposta.data["custo"], "9.90")

    def test_patch_rejeita_quantidade_e_custo_negativos(self):
        casos = (
            ("quantidade_disponivel", "-1.00"),
            ("custo", "-0.01"),
        )
        for campo, valor in casos:
            with self.subTest(campo=campo):
                with patch.object(EstoqueViewSet, "get_object", return_value=self.lote):
                    resposta = self.client.patch("/api/estoque/1/", {campo: valor}, format="json")

                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(campo, resposta.data)

    def test_patch_aceita_custo_nulo(self):
        with (
            patch.object(EstoqueViewSet, "get_object", return_value=self.lote),
            patch.object(EstoqueSerializer, "update", side_effect=self._atualizar),
        ):
            resposta = self.client.patch("/api/estoque/1/", {"custo": None}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIsNone(resposta.data["custo"])

    def test_patch_de_lote_inexistente_retorna_nao_encontrado(self):
        with patch.object(EstoqueViewSet, "get_object", side_effect=Http404):
            resposta = self.client.patch("/api/estoque/999/", {"custo": "1.00"}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_consulta_de_lote_devolve_os_dados_do_produto(self):
        with patch.object(EstoqueViewSet, "get_object", return_value=self.lote):
            resposta = self.client.get("/api/estoque/1/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["id_produto"], 7)
        self.assertEqual(resposta.data["produto_nome"], "Bolo de chocolate")

    def test_disponibilidade_devolve_o_produto_e_o_saldo(self):
        resultado = {
            "quantidade_solicitada": Decimal("3.00"),
            "quantidade_disponivel": Decimal("4.00"),
            "disponivel": True,
            "encaminhar_para_producao": False,
        }
        with (
            patch.object(serializers.PrimaryKeyRelatedField, "to_internal_value", return_value=self.produto),
            patch("estoque.views.Estoque.objects.verificar_disponibilidade", return_value=resultado),
        ):
            resposta = self.client.get(
                "/api/estoque/disponibilidade/", {"id_produto": 7, "quantidade": "3.00"}
            )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["id_produto"], 7)
        self.assertEqual(resposta.data["quantidade_disponivel"], Decimal("4.00"))
        self.assertEqual(resposta.data["quantidade_solicitada"], Decimal("3.00"))

    def test_disponibilidade_exige_produto_e_quantidade(self):
        resposta = self.client.get("/api/estoque/disponibilidade/")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_produto", resposta.data)
        self.assertIn("quantidade", resposta.data)

    def test_disponibilidade_rejeita_quantidades_invalidas(self):
        for quantidade in ("-1", "abc", "1.234", "3,5"):
            with self.subTest(quantidade=quantidade):
                with patch.object(
                    serializers.PrimaryKeyRelatedField, "to_internal_value", return_value=self.produto
                ):
                    resposta = self.client.get(
                        "/api/estoque/disponibilidade/", {"id_produto": 7, "quantidade": quantidade}
                    )

                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("quantidade", resposta.data)

    def test_disponibilidade_rejeita_produto_inexistente(self):
        with patch.object(QuerySet, "get", side_effect=Produto.DoesNotExist):
            resposta = self.client.get(
                "/api/estoque/disponibilidade/", {"id_produto": 999, "quantidade": "1.00"}
            )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_produto", resposta.data)

    def test_disponibilidade_aceita_apenas_consulta_get(self):
        resposta = self.client.post(
            "/api/estoque/disponibilidade/", {"id_produto": 7, "quantidade": "1.00"}, format="json"
        )

        self.assertEqual(resposta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ---------- API: acesso ----------

class EstoqueAcessoApiTests(APITestCase):
    ROTAS = (
        ("get", "/api/estoque/"),
        ("get", "/api/estoque/1/"),
        ("put", "/api/estoque/1/"),
        ("patch", "/api/estoque/1/"),
        ("get", "/api/estoque/disponibilidade/"),
    )

    @staticmethod
    def _chamar(cliente, metodo, rota):
        funcao = getattr(cliente, metodo)
        if metodo == "get":
            return funcao(rota)
        return funcao(rota, {}, format="json")

    def test_usuario_sem_login_nao_acessa_o_estoque(self):
        for metodo, rota in self.ROTAS:
            with self.subTest(rota=rota, metodo=metodo):
                resposta = self._chamar(APIClient(), metodo, rota)

                self.assertIn(
                    resposta.status_code,
                    (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
                )

    def test_exige_troca_da_senha_inicial_em_todas_as_rotas(self):
        cliente = APIClient()
        cliente.force_authenticate(user=_usuario(primeiro_acesso=True))

        for metodo, rota in self.ROTAS:
            with self.subTest(rota=rota, metodo=metodo):
                resposta = self._chamar(cliente, metodo, rota)

                self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)


# ---------- integracao com o banco de dados ----------
# os testes acima usam objetos simulados; estes executam as consultas reais (filtros, ordenacao, soma e rollback)

class EstoqueBancoTests(TestCase):
    def setUp(self):
        self.hoje = timezone.localdate()
        self.produto = Produto.objects.create(nome="Bolo de cenoura", preco_venda=Decimal("30.00"))

    def _lote(self, saldo, dias=None, produto=None):
        validade = None if dias is None else self.hoje + timedelta(days=dias)
        return Estoque.objects.create(
            produto=produto or self.produto,
            quantidade_disponivel=Decimal(saldo),
            data_validade=validade,
        )

    def _saldo(self, lote):
        lote.refresh_from_db()
        return lote.quantidade_disponivel

    def test_baixa_consome_primeiro_o_lote_que_vence_antes(self):
        distante, proximo = self._lote("5.00", dias=20), self._lote("5.00", dias=3)

        baixar_lotes(self.produto.pk, 6)

        self.assertEqual(self._saldo(proximo), Decimal("0.00"))
        self.assertEqual(self._saldo(distante), Decimal("4.00"))

    def test_baixa_ignora_lote_vencido(self):
        vencido, valido = self._lote("9.00", dias=-1), self._lote("2.00", dias=5)

        baixar_lotes(self.produto.pk, 2)

        self.assertEqual(self._saldo(vencido), Decimal("9.00"))
        self.assertEqual(self._saldo(valido), Decimal("0.00"))

    # a ordem entre lotes sem validade (NULL) e com validade depende do banco (SQLite: NULL primeiro; PostgreSQL: NULL por ultimo)
    # por isso o teste confere apenas que lotes sem validade tambem sao consumidos e que nenhum saldo fica negativo
    def test_baixa_tambem_consome_lote_sem_validade(self):
        sem_validade, com_validade = self._lote("4.00"), self._lote("1.00", dias=2)

        baixar_lotes(self.produto.pk, 3)

        saldos = (self._saldo(sem_validade), self._saldo(com_validade))
        self.assertEqual(sum(saldos), Decimal("2.00"))
        self.assertTrue(all(saldo >= 0 for saldo in saldos))

    def test_baixa_so_afeta_lotes_do_produto_informado(self):
        outro = Produto.objects.create(nome="Brigadeiro", preco_venda=Decimal("3.00"))
        lote_outro = self._lote("5.00", dias=1, produto=outro)
        self._lote("5.00", dias=10)

        baixar_lotes(self.produto.pk, 5)

        self.assertEqual(self._saldo(lote_outro), Decimal("5.00"))

    def test_saldo_insuficiente_nao_altera_nenhum_lote(self):
        primeiro, segundo = self._lote("3.00", dias=1), self._lote("2.00", dias=5)

        with self.assertRaises(ValidationError):
            baixar_lotes(self.produto.pk, 6)

        self.assertEqual(self._saldo(primeiro), Decimal("3.00"))
        self.assertEqual(self._saldo(segundo), Decimal("2.00"))

    def test_disponibilidade_soma_apenas_lotes_validos(self):
        self._lote("3.00", dias=0)
        self._lote("2.00", dias=10)
        self._lote("1.00")
        self._lote("50.00", dias=-1)

        resultado = Estoque.objects.verificar_disponibilidade(self.produto.pk, Decimal("6.00"))

        self.assertEqual(resultado["quantidade_disponivel"], Decimal("6.00"))
        self.assertTrue(resultado["disponivel"])
        self.assertFalse(resultado["encaminhar_para_producao"])

    def test_disponibilidade_sem_lotes_validos_encaminha_para_producao(self):
        self._lote("8.00", dias=-5)

        resultado = Estoque.objects.verificar_disponibilidade(self.produto.pk, Decimal("1.00"))

        self.assertEqual(resultado["quantidade_disponivel"], Decimal("0.00"))
        self.assertTrue(resultado["encaminhar_para_producao"])

    def test_disponibilidade_nao_conta_lotes_de_outro_produto(self):
        outro = Produto.objects.create(nome="Torta", preco_venda=Decimal("45.00"))
        self._lote("10.00", produto=outro)

        resultado = Estoque.objects.verificar_disponibilidade(self.produto.pk, Decimal("1.00"))

        self.assertFalse(resultado["disponivel"])


class EstoqueApiBancoTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=_usuario())
        self.produto = Produto.objects.create(nome="Bolo de cenoura", preco_venda=Decimal("30.00"))
        self.lote = Estoque.objects.create(
            produto=self.produto,
            quantidade_disponivel=Decimal("5.00"),
            data_validade=timezone.localdate() + timedelta(days=3),
            custo=Decimal("10.00"),
        )

    def test_lista_lotes_com_nome_do_produto_e_alerta(self):
        resposta = self.client.get("/api/estoque/")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data[0]["produto_nome"], "Bolo de cenoura")
        self.assertEqual(resposta.data[0]["alerta_validade"]["nivel"], "atencao")

    def test_patch_grava_nova_quantidade_no_banco(self):
        resposta = self.client.patch(f"/api/estoque/{self.lote.pk}/", {"quantidade_disponivel": "7.50"}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.quantidade_disponivel, Decimal("7.50"))

    def test_nao_permite_criar_nem_excluir_lotes(self):
        criar = self.client.post(
            "/api/estoque/", {"id_produto": self.produto.pk, "quantidade_disponivel": "1.00"}, format="json"
        )
        excluir = self.client.delete(f"/api/estoque/{self.lote.pk}/")

        self.assertEqual(criar.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(excluir.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Estoque.objects.filter(pk=self.lote.pk).exists())

    def test_disponibilidade_com_dados_reais(self):
        resposta = self.client.get(
            "/api/estoque/disponibilidade/", {"id_produto": self.produto.pk, "quantidade": "8.00"}
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["quantidade_disponivel"], Decimal("5.00"))
        self.assertFalse(resposta.data["disponivel"])
        self.assertTrue(resposta.data["encaminhar_para_producao"])

    def test_disponibilidade_rejeita_produto_inexistente_no_banco(self):
        resposta = self.client.get("/api/estoque/disponibilidade/", {"id_produto": 99999, "quantidade": "1.00"})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_produto", resposta.data)

    def test_produto_com_lotes_nao_pode_ser_excluido(self):
        with self.assertRaises(ProtectedError):
            self.produto.delete()