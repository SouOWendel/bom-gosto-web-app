from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db.models.deletion import ProtectedError
from django.db.transaction import Atomic
from django.http import Http404
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient, APITestCase

from pedido.models import Pedido

from .serializers import (
    AnaliseProducaoSerializer,
    CancelamentoSerializer,
    ConcluirProducaoSerializer,
    ConsumoSerializer,
    IngredienteReceitaSerializer,
    ProdutoAproveitadoSerializer,
    ReceitaProdutoEntradaSerializer,
    ReceitaSerializer,
)
from .services import (
    _consumos_confirmados,
    _ingredientes_previstos,
    analisar_pedido,
    cancelar_pedido,
    concluir_producao,
)
from .views import ReceitaViewSet

# testes complementares do modulo Producao (regras de conclusao, cancelamento, analise, serializers e views)
# usam objetos simulados, como os testes ja existentes em tests.py, para nao depender do banco

DATA_VALIDADE = "2026-11-05"
CONSUMO_PADRAO = [{"ingrediente_id": 1, "quantidade": Decimal("1.50")}]


# ---------- apoio: objetos simulados e ambiente dos servicos ----------

# lista que imita o queryset de ingredientes e registra se houve bloqueio (select_for_update)
class _QuerysetFalso(list):
    bloqueado = False

    def select_for_update(self):
        self.bloqueado = True
        return self


def _usuario(primeiro_acesso=False):
    return SimpleNamespace(is_authenticated=True, primeiro_acesso=primeiro_acesso)


def _ingrediente(pk=1, saldo="4.00", custo="3.00", nome="Farinha", minimo=None, validade=None):
    return SimpleNamespace(
        pk=pk,
        nome=nome,
        quantidade_disponivel=None if saldo is None else Decimal(saldo),
        custo_unitario=None if custo is None else Decimal(custo),
        quantidade_minima=None if minimo is None else Decimal(minimo),
        data_validade=validade,
        save=Mock(),
    )


def _produto(pk=3, receita=None):
    return SimpleNamespace(pk=pk, receita=receita)


def _item(pk=1, produto=None, receita=None, quantidade=1, peso=None):
    return SimpleNamespace(
        pk=pk,
        produto=produto,
        produto_id=produto.pk if produto else None,
        receita=receita,
        quantidade=quantidade,
        quantidade_peso=peso,
    )


def _pedido(estado, tipo=Pedido.Tipo.INTERNO, itens=(), pk=10):
    pedido = SimpleNamespace(pk=pk, tipo=tipo, status=estado, save=Mock())
    pedido.itens = SimpleNamespace(select_related=lambda *args: list(itens))
    return pedido


# evita abrir transacao real e devolve o pedido bloqueado nos servicos
def _simular_transacao(pilha, pedido):
    pilha.enter_context(patch.object(Atomic, "__enter__", return_value=None))
    pilha.enter_context(patch.object(Atomic, "__exit__", return_value=False))
    lock = pilha.enter_context(patch("producao.services.Pedido.objects.select_for_update"))
    lock.return_value.get.return_value = pedido


@contextmanager
def _ambiente_conclusao(pedido, previstos=None, consumos_ok=None, saldo_pronto="0"):
    previstos = ({}, [], []) if previstos is None else previstos
    consumos_ok = [] if consumos_ok is None else consumos_ok
    with ExitStack() as pilha:
        _simular_transacao(pilha, pedido)
        pilha.enter_context(patch("producao.services._ingredientes_previstos", return_value=previstos))
        pilha.enter_context(patch("producao.services._consumos_confirmados", return_value=consumos_ok))
        verificar = pilha.enter_context(
            patch(
                "producao.services.Estoque.objects.verificar_disponibilidade",
                return_value={"quantidade_disponivel": Decimal(saldo_pronto)},
            )
        )
        criar_lote = pilha.enter_context(patch("producao.services.Estoque.objects.create"))
        yield SimpleNamespace(verificar=verificar, criar_lote=criar_lote)


@contextmanager
def _ambiente_cancelamento(pedido, ja_cancelado=False, consumos_ok=None):
    with ExitStack() as pilha:
        _simular_transacao(pilha, pedido)
        filtro = pilha.enter_context(patch("producao.services.Cancelamento.objects.filter"))
        filtro.return_value.exists.return_value = ja_cancelado
        criar_cancelamento = pilha.enter_context(patch("producao.services.Cancelamento.objects.create"))
        confirmados = pilha.enter_context(
            patch("producao.services._consumos_confirmados", return_value=consumos_ok or [])
        )
        criar_produto = pilha.enter_context(patch("producao.services.Produto.objects.create"))
        criar_lote = pilha.enter_context(patch("producao.services.Estoque.objects.create"))
        yield SimpleNamespace(
            criar_cancelamento=criar_cancelamento,
            confirmados=confirmados,
            criar_produto=criar_produto,
            criar_lote=criar_lote,
        )


# ---------- concluir_producao ----------

class ConcluirProducaoRegrasTests(SimpleTestCase):
    def test_recusa_conclusao_de_pedido_que_nao_esta_em_producao(self):
        for estado in (Pedido.Status.PEDIDO_FEITO, Pedido.Status.CONCLUIDO, Pedido.Status.CANCELADO):
            with self.subTest(estado=estado):
                pedido = _pedido(estado)
                with _ambiente_conclusao(pedido) as amb:
                    with self.assertRaises(ValidationError) as erro:
                        concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)
                self.assertIn("status", erro.exception.detail)
                amb.criar_lote.assert_not_called()
                pedido.save.assert_not_called()

    def test_aceita_status_legado_equivalente_a_em_producao(self):
        item = _item(produto=_produto(), quantidade=2)
        pedido = _pedido("pedido_em_producao", itens=[item])
        with _ambiente_conclusao(pedido, consumos_ok=[(_ingrediente(), Decimal("1.00"))]):
            resultado = concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertEqual(pedido.status, Pedido.Status.PRODUCAO_CONCLUIDA)
        self.assertEqual(resultado["custo"], Decimal("3.00"))

    def test_exige_ingredientes_realmente_utilizados(self):
        pedido = _pedido(Pedido.Status.EM_PRODUCAO)
        with _ambiente_conclusao(pedido) as amb:
            with self.assertRaises(ValidationError) as erro:
                concluir_producao(pedido, [], DATA_VALIDADE)

        self.assertIn("consumos", erro.exception.detail)
        amb.criar_lote.assert_not_called()

    def test_recusa_conclusao_quando_ha_ausencias_de_receita(self):
        pedido = _pedido(Pedido.Status.EM_PRODUCAO)
        ausencias = [{"item_pedido": 1, "tipo": "receita", "motivo": "O item não possui receita aplicável."}]
        with _ambiente_conclusao(pedido, previstos=({}, ausencias, [])) as amb:
            with self.assertRaises(ValidationError) as erro:
                concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertIn("receitas", erro.exception.detail)
        amb.criar_lote.assert_not_called()

    def test_exige_informar_todos_os_ingredientes_previstos(self):
        pedido = _pedido(Pedido.Status.EM_PRODUCAO)
        with _ambiente_conclusao(pedido, previstos=({1: {}, 2: {}}, [], [])) as amb:
            with self.assertRaises(ValidationError) as erro:
                concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertIn("ingredientes 2", str(erro.exception.detail["consumos"]))
        amb.criar_lote.assert_not_called()

    def test_recusa_item_sem_produto_e_sem_receita(self):
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=[_item()])
        with _ambiente_conclusao(pedido, consumos_ok=[(_ingrediente(), Decimal("1.00"))]) as amb:
            with self.assertRaises(ValidationError) as erro:
                concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertIn("itens", erro.exception.detail)
        amb.criar_lote.assert_not_called()
        pedido.save.assert_not_called()

    def test_usa_o_produto_da_receita_quando_o_item_so_tem_receita(self):
        produto = _produto(pk=8)
        receita = SimpleNamespace(
            pk=7,
            produtos=SimpleNamespace(order_by=lambda *args: SimpleNamespace(first=lambda: produto)),
        )
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=[_item(receita=receita, quantidade=4)])
        with _ambiente_conclusao(pedido, consumos_ok=[(_ingrediente(), Decimal("1.00"))]) as amb:
            concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        amb.criar_lote.assert_called_once_with(
            produto=produto,
            quantidade_disponivel=Decimal("4"),
            data_validade=DATA_VALIDADE,
            custo=Decimal("3.00"),
        )

    def test_usa_a_relacao_receita_produto_quando_a_receita_nao_tem_produto_direto(self):
        produto = _produto(pk=8)
        receita = SimpleNamespace(
            pk=7,
            produtos=SimpleNamespace(order_by=lambda *args: SimpleNamespace(first=lambda: None)),
        )
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=[_item(receita=receita, quantidade=2)])
        with (
            _ambiente_conclusao(pedido, consumos_ok=[(_ingrediente(), Decimal("1.00"))]) as amb,
            patch("producao.services.ReceitaProduto.objects.filter") as relacao,
        ):
            relacao.return_value.select_related.return_value.first.return_value = SimpleNamespace(produto=produto)
            concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertEqual(amb.criar_lote.call_args.kwargs["produto"], produto)

    def test_recusa_receita_sem_nenhum_produto_associado(self):
        receita = SimpleNamespace(
            pk=7,
            produtos=SimpleNamespace(order_by=lambda *args: SimpleNamespace(first=lambda: None)),
        )
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=[_item(receita=receita, quantidade=2)])
        with (
            _ambiente_conclusao(pedido, consumos_ok=[(_ingrediente(), Decimal("1.00"))]) as amb,
            patch("producao.services.ReceitaProduto.objects.filter") as relacao,
        ):
            relacao.return_value.select_related.return_value.first.return_value = None
            with self.assertRaises(ValidationError) as erro:
                concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertIn("itens", erro.exception.detail)
        amb.criar_lote.assert_not_called()

    def test_pedido_externo_aproveita_o_estoque_pronto_e_produz_so_a_diferenca(self):
        produto = _produto(pk=3)
        pedido = _pedido(
            Pedido.Status.EM_PRODUCAO,
            tipo=Pedido.Tipo.EXTERNO,
            itens=[_item(produto=produto, quantidade=5)],
        )
        with _ambiente_conclusao(
            pedido, consumos_ok=[(_ingrediente(), Decimal("1.00"))], saldo_pronto="3"
        ) as amb:
            concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        amb.verificar.assert_called_once_with(3, Decimal("5"))
        self.assertEqual(amb.criar_lote.call_args.kwargs["quantidade_disponivel"], Decimal("2"))

    def test_pedido_externo_com_saldo_suficiente_nao_gera_lote(self):
        pedido = _pedido(
            Pedido.Status.EM_PRODUCAO,
            tipo=Pedido.Tipo.EXTERNO,
            itens=[_item(produto=_produto(), quantidade=5)],
        )
        with _ambiente_conclusao(
            pedido, consumos_ok=[(_ingrediente(), Decimal("1.00"))], saldo_pronto="10"
        ) as amb:
            concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        amb.criar_lote.assert_not_called()
        self.assertEqual(pedido.status, Pedido.Status.PRODUCAO_CONCLUIDA)

    def test_pedido_interno_ignora_o_saldo_pronto_e_produz_tudo(self):
        pedido = _pedido(
            Pedido.Status.EM_PRODUCAO,
            tipo=Pedido.Tipo.INTERNO,
            itens=[_item(produto=_produto(), quantidade=5)],
        )
        with _ambiente_conclusao(
            pedido, consumos_ok=[(_ingrediente(), Decimal("1.00"))], saldo_pronto="3"
        ) as amb:
            concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        amb.verificar.assert_not_called()
        self.assertEqual(amb.criar_lote.call_args.kwargs["quantidade_disponivel"], Decimal("5"))

    def test_rateia_o_custo_entre_os_lotes_proporcionalmente_a_quantidade(self):
        itens = [
            _item(pk=1, produto=_produto(pk=3), quantidade=1),
            _item(pk=2, produto=_produto(pk=4), quantidade=3),
        ]
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=itens)
        ingrediente = _ingrediente(custo="4.00")
        with _ambiente_conclusao(pedido, consumos_ok=[(ingrediente, Decimal("1.00"))]) as amb:
            resultado = concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        custos = [chamada.kwargs["custo"] for chamada in amb.criar_lote.call_args_list]
        self.assertEqual(resultado["custo"], Decimal("4.00"))
        self.assertEqual(custos, [Decimal("1.00"), Decimal("3.00")])

    def test_rateio_arredonda_cada_lote_em_centavos(self):
        # comportamento atual: 10,00 dividido em 3 lotes iguais gera 3,33 em cada (soma 9,99)
        itens = [_item(pk=n, produto=_produto(pk=n + 10), quantidade=1) for n in range(1, 4)]
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=itens)
        ingrediente = _ingrediente(custo="10.00")
        with _ambiente_conclusao(pedido, consumos_ok=[(ingrediente, Decimal("1.00"))]) as amb:
            concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        custos = [chamada.kwargs["custo"] for chamada in amb.criar_lote.call_args_list]
        self.assertEqual(custos, [Decimal("3.33")] * 3)

    def test_ingrediente_sem_custo_cadastrado_conta_como_custo_zero(self):
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=[_item(produto=_produto(), quantidade=2)])
        ingrediente = _ingrediente(custo=None)
        with _ambiente_conclusao(pedido, consumos_ok=[(ingrediente, Decimal("1.00"))]):
            resultado = concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertEqual(resultado["custo"], Decimal("0"))

    def test_consumo_zero_nao_altera_o_saldo_e_nao_gera_custo(self):
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=[_item(produto=_produto(), quantidade=2)])
        ingrediente = _ingrediente(saldo="4.00")
        with _ambiente_conclusao(pedido, consumos_ok=[(ingrediente, Decimal("0"))]):
            resultado = concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertEqual(ingrediente.quantidade_disponivel, Decimal("4.00"))
        self.assertEqual(resultado["custo"], Decimal("0"))

    def test_ingrediente_sem_saldo_registrado_parte_de_zero_na_baixa(self):
        pedido = _pedido(Pedido.Status.EM_PRODUCAO, itens=[_item(produto=_produto(), quantidade=2)])
        ingrediente = _ingrediente(saldo=None)
        with _ambiente_conclusao(pedido, consumos_ok=[(ingrediente, Decimal("0"))]):
            concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertEqual(ingrediente.quantidade_disponivel, Decimal("0"))


# ---------- _consumos_confirmados ----------

class ConsumosConfirmadosTests(SimpleTestCase):
    # metodo auxiliar que simula a consulta de ingredientes e devolve o resultado e o queryset falso
    def _confirmar(self, ingredientes, consumos, lock=False):
        qs = _QuerysetFalso(ingredientes)
        with patch(
            "producao.services.Ingrediente.objects.filter",
            return_value=SimpleNamespace(order_by=lambda *args: qs),
        ):
            return _consumos_confirmados(consumos, lock=lock), qs

    def test_soma_linhas_repetidas_do_mesmo_ingrediente(self):
        ingrediente = _ingrediente(saldo="5.00")
        consumos = [
            {"ingrediente_id": 1, "quantidade": Decimal("1.00")},
            {"ingrediente_id": 1, "quantidade": Decimal("2.50")},
        ]

        resultado, _ = self._confirmar([ingrediente], consumos)

        self.assertEqual(resultado, [(ingrediente, Decimal("3.50"))])

    def test_rejeita_soma_repetida_que_ultrapassa_o_saldo(self):
        ingrediente = _ingrediente(saldo="3.00")
        consumos = [
            {"ingrediente_id": 1, "quantidade": Decimal("2.00")},
            {"ingrediente_id": 1, "quantidade": Decimal("2.00")},
        ]

        with self.assertRaises(ValidationError):
            self._confirmar([ingrediente], consumos)

    def test_aceita_consumo_igual_ao_saldo(self):
        ingrediente = _ingrediente(saldo="4.00")

        resultado, _ = self._confirmar(
            [ingrediente], [{"ingrediente_id": 1, "quantidade": Decimal("4.00")}]
        )

        self.assertEqual(resultado, [(ingrediente, Decimal("4.00"))])

    def test_rejeita_saldo_insuficiente_informando_o_ingrediente(self):
        ingrediente = _ingrediente(saldo="1.00", nome="Chocolate")

        with self.assertRaises(ValidationError) as erro:
            self._confirmar([ingrediente], [{"ingrediente_id": 1, "quantidade": Decimal("1.01")}])

        self.assertIn("Chocolate", str(erro.exception.detail["consumos"]))

    def test_rejeita_ingrediente_inexistente(self):
        with self.assertRaises(ValidationError) as erro:
            self._confirmar([], [{"ingrediente_id": 99, "quantidade": Decimal("1.00")}])

        self.assertIn("consumos", erro.exception.detail)

    def test_rejeita_quantidade_negativa(self):
        ingrediente = _ingrediente(saldo="4.00")

        with self.assertRaises(ValidationError) as erro:
            self._confirmar([ingrediente], [{"ingrediente_id": 1, "quantidade": Decimal("-1.00")}])

        self.assertIn("consumos", erro.exception.detail)

    def test_saldo_nao_registrado_conta_como_zero(self):
        ingrediente = _ingrediente(saldo=None)

        resultado, _ = self._confirmar(
            [ingrediente], [{"ingrediente_id": 1, "quantidade": Decimal("0")}]
        )
        self.assertEqual(resultado, [(ingrediente, Decimal("0"))])

        with self.assertRaises(ValidationError):
            self._confirmar([ingrediente], [{"ingrediente_id": 1, "quantidade": Decimal("1.00")}])

    def test_bloqueia_os_ingredientes_somente_quando_solicitado(self):
        consumos = [{"ingrediente_id": 1, "quantidade": Decimal("1.00")}]

        _, com_bloqueio = self._confirmar([_ingrediente()], consumos, lock=True)
        _, sem_bloqueio = self._confirmar([_ingrediente()], consumos, lock=False)

        self.assertTrue(com_bloqueio.bloqueado)
        self.assertFalse(sem_bloqueio.bloqueado)


# ---------- _ingredientes_previstos ----------

@contextmanager
def _composicao(componentes):
    with patch("producao.services.IngredienteReceita.objects.filter") as filtro:
        filtro.return_value.select_related.return_value.order_by.return_value = componentes
        yield filtro


def _componente(ingrediente, quantidade):
    return SimpleNamespace(
        ingrediente_id=ingrediente.pk,
        ingrediente=ingrediente,
        quantidade_necessaria=Decimal(quantidade),
    )


def _receita(rendimento="10", nome="Bolo"):
    return SimpleNamespace(
        pk=7,
        nome=nome,
        rendimento_quantidade=None if rendimento is None else Decimal(rendimento),
    )


class IngredientesPrevistosTests(SimpleTestCase):
    def test_calcula_o_necessario_proporcional_ao_rendimento(self):
        ingrediente = _ingrediente()
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO, itens=[_item(receita=_receita("10"), quantidade=5)])

        with _composicao([_componente(ingrediente, "2.00")]):
            previstos, ausencias, sugestoes = _ingredientes_previstos(pedido)

        self.assertEqual(previstos[1]["necessario"], Decimal("1.00"))
        self.assertEqual(ausencias, [])
        self.assertEqual(sugestoes, [])

    def test_soma_o_mesmo_ingrediente_de_itens_diferentes(self):
        ingrediente = _ingrediente()
        itens = [
            _item(pk=1, receita=_receita("10"), quantidade=5),
            _item(pk=2, receita=_receita("10"), quantidade=5),
        ]
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO, itens=itens)

        with _composicao([_componente(ingrediente, "2.00")]):
            previstos, _, _ = _ingredientes_previstos(pedido)

        self.assertEqual(previstos[1]["necessario"], Decimal("2.00"))

    def test_arredonda_o_necessario_para_centavos_com_meio_para_cima(self):
        ingrediente = _ingrediente()
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO, itens=[_item(receita=_receita("10"), quantidade=1)])

        with _composicao([_componente(ingrediente, "0.05")]):
            previstos, _, _ = _ingredientes_previstos(pedido)

        self.assertEqual(previstos[1]["necessario"], Decimal("0.01"))

    def test_registra_ausencia_quando_o_item_nao_tem_receita(self):
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO, itens=[_item(pk=4)])

        previstos, ausencias, _ = _ingredientes_previstos(pedido)

        self.assertEqual(previstos, {})
        self.assertEqual(ausencias[0]["tipo"], "receita")
        self.assertEqual(ausencias[0]["item_pedido"], 4)

    def test_registra_ausencia_quando_o_rendimento_e_invalido(self):
        for rendimento in (None, "0"):
            with self.subTest(rendimento=rendimento):
                pedido = _pedido(
                    Pedido.Status.PEDIDO_FEITO,
                    itens=[_item(receita=_receita(rendimento), quantidade=2)],
                )

                previstos, ausencias, _ = _ingredientes_previstos(pedido)

                self.assertEqual(previstos, {})
                self.assertEqual(ausencias[0]["tipo"], "rendimento")

    def test_registra_ausencia_quando_a_receita_nao_tem_ingredientes(self):
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO, itens=[_item(receita=_receita("10"), quantidade=2)])

        with _composicao([]):
            previstos, ausencias, _ = _ingredientes_previstos(pedido)

        self.assertEqual(previstos, {})
        self.assertEqual(ausencias[0]["tipo"], "ingredientes")
        self.assertIn("Bolo", ausencias[0]["motivo"])

    def test_pedido_externo_abate_o_saldo_pronto_da_necessidade(self):
        ingrediente = _ingrediente()
        receita = _receita("10")
        produto = _produto(pk=3, receita=receita)
        pedido = _pedido(
            Pedido.Status.PEDIDO_FEITO,
            tipo=Pedido.Tipo.EXTERNO,
            itens=[_item(produto=produto, quantidade=5)],
        )

        with (
            _composicao([_componente(ingrediente, "2.00")]),
            patch(
                "producao.services.Estoque.objects.verificar_disponibilidade",
                return_value={"quantidade_disponivel": Decimal("2")},
            ),
        ):
            previstos, _, _ = _ingredientes_previstos(pedido)

        self.assertEqual(previstos[1]["necessario"], Decimal("0.60"))

    def test_pedido_externo_totalmente_atendido_pelo_estoque_nao_exige_ingredientes(self):
        receita = _receita("10")
        pedido = _pedido(
            Pedido.Status.PEDIDO_FEITO,
            tipo=Pedido.Tipo.EXTERNO,
            itens=[_item(produto=_produto(pk=3, receita=receita), quantidade=5)],
        )

        with (
            _composicao([]) as filtro,
            patch(
                "producao.services.Estoque.objects.verificar_disponibilidade",
                return_value={"quantidade_disponivel": Decimal("5")},
            ),
        ):
            previstos, ausencias, _ = _ingredientes_previstos(pedido)

        self.assertEqual(previstos, {})
        self.assertEqual(ausencias, [])
        filtro.assert_not_called()

    def test_pedido_interno_nao_consulta_o_estoque_pronto(self):
        ingrediente = _ingrediente()
        receita = _receita("10")
        pedido = _pedido(
            Pedido.Status.PEDIDO_FEITO,
            tipo=Pedido.Tipo.INTERNO,
            itens=[_item(produto=_produto(pk=3, receita=receita), quantidade=5)],
        )

        with (
            _composicao([_componente(ingrediente, "2.00")]),
            patch("producao.services.Estoque.objects.verificar_disponibilidade") as verificar,
        ):
            previstos, _, _ = _ingredientes_previstos(pedido)

        verificar.assert_not_called()
        self.assertEqual(previstos[1]["necessario"], Decimal("1.00"))

    def test_produto_sem_receita_sugere_as_receitas_associadas(self):
        pedido = _pedido(
            Pedido.Status.PEDIDO_FEITO,
            itens=[_item(produto=_produto(pk=3, receita=None), quantidade=2)],
        )

        with (
            patch("producao.services.ReceitaProduto.objects.filter") as relacao,
            patch("producao.services.Receita.objects.filter") as receitas,
        ):
            relacao.return_value.values_list.return_value = [7]
            receitas.return_value.order_by.return_value = [SimpleNamespace(pk=7, nome="Bolo")]
            previstos, ausencias, sugestoes = _ingredientes_previstos(pedido)

        self.assertEqual(previstos, {})
        self.assertEqual(ausencias, [])
        self.assertEqual(sugestoes, [{"id_receita": 7, "nome": "Bolo"}])

    def test_produto_sem_nenhuma_receita_associada_gera_ausencia(self):
        pedido = _pedido(
            Pedido.Status.PEDIDO_FEITO,
            itens=[_item(pk=9, produto=_produto(pk=3, receita=None), quantidade=2)],
        )

        with (
            patch("producao.services.ReceitaProduto.objects.filter") as relacao,
            patch("producao.services.Receita.objects.filter") as receitas,
        ):
            relacao.return_value.values_list.return_value = []
            receitas.return_value.order_by.return_value = []
            _, ausencias, sugestoes = _ingredientes_previstos(pedido)

        self.assertEqual(sugestoes, [])
        self.assertEqual(ausencias[0]["tipo"], "receita")
        self.assertEqual(ausencias[0]["item_pedido"], 9)


# ---------- analisar_pedido ----------

class AnalisarPedidoTests(SimpleTestCase):
    # metodo auxiliar que roda a analise com ingredientes previstos e saldo pronto simulados
    def _analisar(self, itens, previstos, saldo=None, hoje=None):
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO, itens=itens)
        saldo = saldo or {
            "quantidade_solicitada": 2,
            "quantidade_disponivel": Decimal("0"),
            "disponivel": False,
            "encaminhar_para_producao": True,
        }
        with (
            patch("producao.services._ingredientes_previstos", return_value=(previstos, [], [])),
            patch("producao.services.Estoque.objects.verificar_disponibilidade", return_value=saldo),
            patch("producao.services.timezone.localdate", return_value=hoje or date(2026, 1, 1)),
        ):
            return analisar_pedido(pedido)

    def test_destaca_ingrediente_com_saldo_insuficiente(self):
        ingrediente = _ingrediente(saldo="1.00", minimo="2.00")
        previstos = {1: {"ingrediente": ingrediente, "necessario": Decimal("3.00")}}

        resultado = self._analisar([_item(quantidade=2)], previstos)

        linha = resultado["ingredientes"][0]
        self.assertFalse(linha["suficiente"])
        self.assertTrue(linha["abaixo_do_minimo"])
        self.assertEqual(len(resultado["ingredientes_insuficientes"]), 1)

    def test_ingrediente_com_saldo_suficiente_nao_aparece_como_insuficiente(self):
        ingrediente = _ingrediente(saldo="5.00", minimo="2.00")
        previstos = {1: {"ingrediente": ingrediente, "necessario": Decimal("3.00")}}

        resultado = self._analisar([_item(quantidade=2)], previstos)

        self.assertTrue(resultado["ingredientes"][0]["suficiente"])
        self.assertFalse(resultado["ingredientes"][0]["abaixo_do_minimo"])
        self.assertEqual(resultado["ingredientes_insuficientes"], [])

    def test_saldo_igual_ao_necessario_e_suficiente(self):
        ingrediente = _ingrediente(saldo="3.00")
        previstos = {1: {"ingrediente": ingrediente, "necessario": Decimal("3.00")}}

        resultado = self._analisar([_item(quantidade=2)], previstos)

        self.assertTrue(resultado["ingredientes"][0]["suficiente"])

    def test_ingrediente_sem_saldo_registrado_conta_como_zero(self):
        ingrediente = _ingrediente(saldo=None)
        previstos = {1: {"ingrediente": ingrediente, "necessario": Decimal("1.00")}}

        resultado = self._analisar([_item(quantidade=2)], previstos)

        self.assertEqual(resultado["ingredientes"][0]["disponivel"], Decimal("0"))
        self.assertFalse(resultado["ingredientes"][0]["suficiente"])

    def test_sem_minimo_cadastrado_nao_esta_abaixo_do_minimo(self):
        ingrediente = _ingrediente(saldo="1.00", minimo=None)
        previstos = {1: {"ingrediente": ingrediente, "necessario": Decimal("0.50")}}

        resultado = self._analisar([_item(quantidade=2)], previstos)

        self.assertFalse(resultado["ingredientes"][0]["abaixo_do_minimo"])

    def test_alerta_de_validade_do_ingrediente_usado(self):
        hoje = date(2026, 1, 1)
        casos = [
            (None, None),
            (hoje + timedelta(days=30), None),
            (hoje + timedelta(days=3), {"nivel": "atencao", "dias_para_vencer": 3}),
            (hoje - timedelta(days=1), {"nivel": "critico", "dias_para_vencer": -1}),
        ]
        for validade, esperado in casos:
            with self.subTest(validade=validade):
                ingrediente = _ingrediente(saldo="5.00", validade=validade)
                previstos = {1: {"ingrediente": ingrediente, "necessario": Decimal("1.00")}}

                resultado = self._analisar([_item(quantidade=2)], previstos, hoje=hoje)

                self.assertEqual(resultado["ingredientes"][0]["alerta_validade"], esperado)

    def test_item_sem_produto_e_encaminhado_para_producao(self):
        resultado = self._analisar([_item(pk=5, quantidade=2)], {})

        self.assertTrue(resultado["encaminhar_para_producao"])
        self.assertFalse(resultado["estoque"][0]["disponivel"])
        self.assertEqual(resultado["estoque"][0]["id_item_pedido"], 5)
        self.assertIsNone(resultado["estoque"][0]["produto_id"])

    def test_item_atendido_pelo_estoque_nao_e_encaminhado_para_producao(self):
        saldo = {
            "quantidade_solicitada": 2,
            "quantidade_disponivel": Decimal("5"),
            "disponivel": True,
            "encaminhar_para_producao": False,
        }

        resultado = self._analisar(
            [_item(pk=5, produto=_produto(pk=3), quantidade=2)], {}, saldo=saldo
        )

        self.assertFalse(resultado["encaminhar_para_producao"])
        self.assertEqual(resultado["estoque"][0]["produto_id"], 3)


# ---------- serializers ----------

class ConsumoSerializerTests(SimpleTestCase):
    def test_quantidade_nao_aceita_valor_negativo(self):
        campo = ConsumoSerializer().fields["quantidade"]

        with self.assertRaises(ValidationError):
            campo.run_validation("-0.01")

    def test_quantidade_aceita_zero_e_valores_positivos(self):
        campo = ConsumoSerializer().fields["quantidade"]

        self.assertEqual(campo.run_validation("0.00"), Decimal("0.00"))
        self.assertEqual(campo.run_validation("1.50"), Decimal("1.50"))

    def test_representacao_devolve_id_do_ingrediente_e_quantidade(self):
        representacao = ConsumoSerializer().to_representation(
            {"ingrediente": SimpleNamespace(pk=4), "quantidade": Decimal("1.50")}
        )

        self.assertEqual(representacao, {"ingrediente_id": 4, "quantidade": Decimal("1.50")})


class ReceitaSerializersTests(SimpleTestCase):
    def test_composicao_exige_quantidade_maior_que_zero(self):
        serializer = IngredienteReceitaSerializer()

        for valor in (Decimal("0"), Decimal("-1.00")):
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    serializer.validate_quantidade_necessaria(valor)
        self.assertEqual(serializer.validate_quantidade_necessaria(Decimal("0.01")), Decimal("0.01"))

    def test_relacao_com_produto_exige_quantidade_maior_que_zero(self):
        serializer = ReceitaProdutoEntradaSerializer()

        with self.assertRaises(ValidationError):
            serializer.validate_quantidade(Decimal("0"))
        self.assertEqual(serializer.validate_quantidade(Decimal("1")), Decimal("1"))

    def test_relacao_com_produto_nao_aceita_custo_negativo(self):
        serializer = ReceitaProdutoEntradaSerializer()

        with self.assertRaises(ValidationError):
            serializer.validate_custo_unitario(Decimal("-0.01"))
        self.assertIsNone(serializer.validate_custo_unitario(None))
        self.assertEqual(serializer.validate_custo_unitario(Decimal("0")), Decimal("0"))

    def test_rendimento_da_receita_deve_ser_maior_que_zero(self):
        serializer = ReceitaSerializer()

        for valor in (Decimal("0"), Decimal("-1")):
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    serializer.validate_rendimento_quantidade(valor)
        self.assertIsNone(serializer.validate_rendimento_quantidade(None))
        self.assertEqual(serializer.validate_rendimento_quantidade(Decimal("12")), Decimal("12"))

    def test_rejeita_ingrediente_repetido_na_receita(self):
        attrs = {
            "composicao": [
                {"ingrediente": SimpleNamespace(pk=1)},
                {"ingrediente": SimpleNamespace(pk=1)},
            ]
        }

        with self.assertRaises(ValidationError) as erro:
            ReceitaSerializer().validate(attrs)

        self.assertIn("ingredientes", erro.exception.detail)

    def test_rejeita_produto_repetido_na_receita(self):
        attrs = {
            "produtos_relacionados": [
                {"produto": SimpleNamespace(pk=3)},
                {"produto": SimpleNamespace(pk=3)},
            ]
        }

        with self.assertRaises(ValidationError) as erro:
            ReceitaSerializer().validate(attrs)

        self.assertIn("produtos_relacionados", erro.exception.detail)

    def test_aceita_ingredientes_e_produtos_distintos(self):
        attrs = {
            "composicao": [
                {"ingrediente": SimpleNamespace(pk=1)},
                {"ingrediente": SimpleNamespace(pk=2)},
            ],
            "produtos_relacionados": [
                {"produto": SimpleNamespace(pk=3)},
                {"produto": SimpleNamespace(pk=4)},
            ],
        }

        self.assertEqual(ReceitaSerializer().validate(attrs), attrs)


class ProdutoAproveitadoSerializerTests(SimpleTestCase):
    DADOS = {
        "nome": "Bolo parcial",
        "quantidade": "2.00",
        "data_validade": "2026-11-10",
        "preco_venda": "8.00",
        "custo": "5.00",
    }

    def _serializer(self, **mudancas):
        dados = {**self.DADOS, **mudancas}
        dados = {campo: valor for campo, valor in dados.items() if valor is not None}
        return ProdutoAproveitadoSerializer(data=dados)

    def test_aceita_dados_completos(self):
        serializer = self._serializer()

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejeita_dados_invalidos(self):
        casos = {
            "quantidade": "0.00",
            "preco_venda": "-1.00",
            "custo": "-1.00",
            "nome": "",
            "data_validade": "10/11/2026",
        }
        for campo, valor in casos.items():
            with self.subTest(campo=campo):
                serializer = self._serializer(**{campo: valor})

                self.assertFalse(serializer.is_valid())
                self.assertIn(campo, serializer.errors)

    def test_exige_todos_os_campos(self):
        for campo in self.DADOS:
            with self.subTest(campo=campo):
                serializer = self._serializer(**{campo: None})

                self.assertFalse(serializer.is_valid())
                self.assertIn(campo, serializer.errors)


class CancelamentoSerializerTests(SimpleTestCase):
    PRODUTO = {
        "nome": "Bolo parcial",
        "quantidade": "2.00",
        "data_validade": "2026-11-10",
        "preco_venda": "8.00",
        "custo": "5.00",
    }

    def test_aceita_descarte_sem_consumos(self):
        serializer = CancelamentoSerializer(data={"consumos": [], "destino": "descarte"})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejeita_destino_desconhecido(self):
        serializer = CancelamentoSerializer(data={"consumos": [], "destino": "doacao"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("destino", serializer.errors)

    def test_destino_estoque_exige_produto_aproveitado(self):
        serializer = CancelamentoSerializer(data={"consumos": [], "destino": "estoque"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("produto_aproveitado", serializer.errors)

    def test_aceita_destino_estoque_com_produto_aproveitado(self):
        serializer = CancelamentoSerializer(
            data={"consumos": [], "destino": "estoque", "produto_aproveitado": self.PRODUTO}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_exige_a_lista_de_consumos(self):
        serializer = CancelamentoSerializer(data={"destino": "descarte"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("consumos", serializer.errors)

    def test_salvar_chama_o_servico_de_cancelamento_com_os_dados_validados(self):
        pedido = SimpleNamespace(pk=1)
        serializer = CancelamentoSerializer(
            data={"consumos": [], "destino": "descarte"}, context={"pedido": pedido}
        )
        serializer.is_valid(raise_exception=True)

        with patch("producao.serializers.cancelar_pedido", return_value=("pedido", "cancelamento")) as cancelar:
            resultado = serializer.save()

        cancelar.assert_called_once_with(pedido, [], "descarte", None)
        self.assertEqual(resultado, ("pedido", "cancelamento"))


class ConcluirProducaoSerializerTests(SimpleTestCase):
    def test_exige_ao_menos_um_consumo(self):
        serializer = ConcluirProducaoSerializer(data={"data_validade": DATA_VALIDADE, "consumos": []})

        self.assertFalse(serializer.is_valid())
        self.assertIn("consumos", serializer.errors)

    def test_exige_data_de_validade(self):
        serializer = ConcluirProducaoSerializer(data={"consumos": []})

        self.assertFalse(serializer.is_valid())
        self.assertIn("data_validade", serializer.errors)

    def test_rejeita_data_de_validade_em_formato_invalido(self):
        serializer = ConcluirProducaoSerializer(data={"data_validade": "05/11/2026", "consumos": []})

        self.assertFalse(serializer.is_valid())
        self.assertIn("data_validade", serializer.errors)

    def test_criar_converte_ingredientes_em_ids_antes_de_concluir(self):
        pedido = SimpleNamespace(pk=1)
        serializer = ConcluirProducaoSerializer(context={"pedido": pedido})
        dados = {
            "data_validade": date(2026, 11, 5),
            "consumos": [
                {"ingrediente": SimpleNamespace(pk=1), "quantidade": Decimal("2.00")},
                {"ingrediente": SimpleNamespace(pk=2), "quantidade": Decimal("0")},
            ],
        }

        with patch("producao.serializers.concluir_producao", return_value={"custo": Decimal("1.00")}) as concluir:
            resultado = serializer.create(dados)

        concluir.assert_called_once_with(
            pedido,
            [
                {"ingrediente_id": 1, "quantidade": Decimal("2.00")},
                {"ingrediente_id": 2, "quantidade": Decimal("0")},
            ],
            date(2026, 11, 5),
        )
        self.assertEqual(resultado, {"custo": Decimal("1.00")})


# ---------- cancelar_pedido ----------

class CancelarPedidoRegrasTests(SimpleTestCase):
    PRODUTO = {
        "nome": "Bolo parcial",
        "preco_venda": Decimal("8.00"),
        "quantidade": Decimal("2.00"),
        "data_validade": date(2026, 11, 10),
        "custo": Decimal("5.00"),
    }

    def test_recusa_cancelar_pedido_concluido_ou_ja_cancelado(self):
        for estado in (Pedido.Status.CONCLUIDO, Pedido.Status.CANCELADO, "pedido_cancelado"):
            with self.subTest(estado=estado):
                pedido = _pedido(estado)
                with _ambiente_cancelamento(pedido) as amb:
                    with self.assertRaises(ValidationError) as erro:
                        cancelar_pedido(pedido, [], "descarte")

                self.assertIn("status", erro.exception.detail)
                amb.criar_cancelamento.assert_not_called()
                pedido.save.assert_not_called()

    def test_recusa_descarte_de_pedido_com_producao_concluida(self):
        pedido = _pedido(Pedido.Status.PRODUCAO_CONCLUIDA)
        with _ambiente_cancelamento(pedido) as amb:
            with self.assertRaises(ValidationError) as erro:
                cancelar_pedido(pedido, [], "descarte")

        self.assertIn("destino", erro.exception.detail)
        amb.criar_cancelamento.assert_not_called()
        pedido.save.assert_not_called()

    def test_recusa_segundo_cancelamento_do_mesmo_pedido(self):
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO)
        with _ambiente_cancelamento(pedido, ja_cancelado=True) as amb:
            with self.assertRaises(ValidationError) as erro:
                cancelar_pedido(pedido, [], "descarte")

        self.assertIn("pedido", erro.exception.detail)
        amb.criar_cancelamento.assert_not_called()

    def test_baixa_os_ingredientes_informados_no_cancelamento(self):
        ingrediente = _ingrediente(saldo="4.00")
        pedido = _pedido(Pedido.Status.EM_PRODUCAO)
        with _ambiente_cancelamento(pedido, consumos_ok=[(ingrediente, Decimal("1.50"))]) as amb:
            cancelar_pedido(pedido, CONSUMO_PADRAO, "descarte")

        amb.confirmados.assert_called_once_with(CONSUMO_PADRAO, lock=True)
        self.assertEqual(ingrediente.quantidade_disponivel, Decimal("2.50"))
        ingrediente.save.assert_called_once_with(update_fields=["quantidade_disponivel"])

    def test_registra_destino_data_e_muda_o_status(self):
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO)
        with (
            _ambiente_cancelamento(pedido) as amb,
            patch("producao.services.timezone.localdate", return_value=date(2026, 11, 9)),
        ):
            resultado, cancelamento = cancelar_pedido(pedido, [], "descarte")

        amb.criar_cancelamento.assert_called_once_with(
            pedido=pedido, destino="descarte", data_cancelamento=date(2026, 11, 9)
        )
        self.assertEqual(cancelamento, amb.criar_cancelamento.return_value)
        self.assertEqual(resultado.status, Pedido.Status.CANCELADO)
        pedido.save.assert_called_once_with(update_fields=["status"])

    def test_destino_estoque_exige_dados_do_produto_aproveitado(self):
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO)
        with _ambiente_cancelamento(pedido) as amb:
            with self.assertRaises(ValidationError) as erro:
                cancelar_pedido(pedido, [], "estoque")

        self.assertIn("produto_aproveitado", erro.exception.detail)
        amb.criar_cancelamento.assert_not_called()
        amb.criar_lote.assert_not_called()

    def test_destino_estoque_cria_produto_e_lote_reaproveitado(self):
        pedido = _pedido(Pedido.Status.EM_PRODUCAO)
        with _ambiente_cancelamento(pedido) as amb:
            cancelar_pedido(pedido, [], "estoque", self.PRODUTO)

        amb.criar_produto.assert_called_once_with(nome="Bolo parcial", preco_venda=Decimal("8.00"))
        amb.criar_lote.assert_called_once_with(
            produto=amb.criar_produto.return_value,
            quantidade_disponivel=Decimal("2.00"),
            data_validade=date(2026, 11, 10),
            custo=Decimal("5.00"),
        )

    def test_producao_concluida_nao_repete_baixa_nem_nova_entrada_no_estoque(self):
        pedido = _pedido(Pedido.Status.PRODUCAO_CONCLUIDA)
        with _ambiente_cancelamento(pedido) as amb:
            resultado, _ = cancelar_pedido(pedido, CONSUMO_PADRAO, "estoque", self.PRODUTO)

        amb.confirmados.assert_not_called()
        amb.criar_produto.assert_not_called()
        amb.criar_lote.assert_not_called()
        amb.criar_cancelamento.assert_called_once()
        self.assertEqual(resultado.status, Pedido.Status.CANCELADO)


# ---------- views ----------

class ProducaoViewsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=_usuario())

    # metodo auxiliar que chama a rota de iniciar com o pedido e o serializer simulados
    def _iniciar(self, pedido):
        with (
            patch("producao.views.get_object_or_404", return_value=pedido),
            patch("producao.views.PedidoSerializer") as serializer,
        ):
            serializer.return_value.data = {"status": "em_producao"}
            return self.client.post("/api/producao/pedidos/1/iniciar/", {}, format="json")

    def test_inicia_a_producao_de_pedido_feito(self):
        pedido = SimpleNamespace(status=Pedido.Status.PEDIDO_FEITO, save=Mock())

        resposta = self._iniciar(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(pedido.status, Pedido.Status.EM_PRODUCAO)
        pedido.save.assert_called_once_with(update_fields=["status"])

    def test_aceita_status_legado_equivalente_a_pedido_feito(self):
        pedido = SimpleNamespace(status="pagamento_total", save=Mock())

        resposta = self._iniciar(pedido)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(pedido.status, Pedido.Status.EM_PRODUCAO)

    def test_recusa_iniciar_producao_fora_do_status_pedido_feito(self):
        estados = (
            Pedido.Status.EM_PRODUCAO,
            Pedido.Status.PRODUCAO_CONCLUIDA,
            Pedido.Status.CONCLUIDO,
            Pedido.Status.CANCELADO,
            "pagamento_parcial",
        )
        for estado in estados:
            with self.subTest(estado=estado):
                pedido = SimpleNamespace(status=estado, save=Mock())

                resposta = self._iniciar(pedido)

                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("status", resposta.data)
                pedido.save.assert_not_called()

    def test_validar_devolve_a_analise_do_pedido(self):
        with (
            patch("producao.views.get_object_or_404", return_value=SimpleNamespace(pk=1)),
            patch("producao.services.analisar_pedido", return_value={"ingredientes": []}) as analisar,
        ):
            resposta = self.client.post("/api/producao/pedidos/1/validar/", {}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data, {"ingredientes": []})
        analisar.assert_called_once()

    def test_concluir_recusa_payload_sem_consumos(self):
        with patch("producao.views.get_object_or_404", return_value=SimpleNamespace(pk=1)):
            resposta = self.client.post(
                "/api/producao/pedidos/1/concluir/",
                {"data_validade": DATA_VALIDADE, "consumos": []},
                format="json",
            )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("consumos", resposta.data)

    def test_concluir_devolve_pedido_e_custo_de_producao(self):
        pedido = SimpleNamespace(pk=1)
        payload = {"data_validade": DATA_VALIDADE, "consumos": []}
        with (
            patch("producao.views.get_object_or_404", return_value=pedido),
            patch("producao.views.ConcluirProducaoSerializer") as classe,
            patch("producao.views.PedidoSerializer") as pedido_serializer,
        ):
            classe.return_value.save.return_value = {"pedido": pedido, "custo": Decimal("4.50")}
            pedido_serializer.return_value.data = {"status": "producao_concluida"}
            resposta = self.client.post("/api/producao/pedidos/1/concluir/", payload, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["custo_producao"], Decimal("4.50"))
        self.assertEqual(resposta.data["pedido"], {"status": "producao_concluida"})
        classe.assert_called_once_with(data=payload, context={"pedido": pedido})
        classe.return_value.is_valid.assert_called_once_with(raise_exception=True)

    def test_retorna_nao_encontrado_para_pedido_inexistente(self):
        for rota in ("validar", "iniciar", "concluir"):
            with self.subTest(rota=rota):
                with patch("producao.views.get_object_or_404", side_effect=Http404):
                    resposta = self.client.post(f"/api/producao/pedidos/999/{rota}/", {}, format="json")

                self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)


class ProducaoAcessoApiTests(APITestCase):
    ROTAS = (
        ("get", "/api/producao/receitas/"),
        ("post", "/api/producao/pedidos/1/validar/"),
        ("post", "/api/producao/pedidos/1/iniciar/"),
        ("post", "/api/producao/pedidos/1/concluir/"),
    )

    def _chamar(self, cliente, metodo, rota):
        funcao = getattr(cliente, metodo)
        if metodo == "get":
            return funcao(rota)
        return funcao(rota, {}, format="json")

    def test_usuario_sem_login_nao_acessa_a_producao(self):
        for metodo, rota in self.ROTAS:
            with self.subTest(rota=rota):
                resposta = self._chamar(APIClient(), metodo, rota)

                self.assertIn(
                    resposta.status_code,
                    (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
                )

    def test_exige_troca_da_senha_inicial_em_todas_as_rotas(self):
        cliente = APIClient()
        cliente.force_authenticate(user=_usuario(primeiro_acesso=True))

        for metodo, rota in self.ROTAS:
            with self.subTest(rota=rota):
                resposta = self._chamar(cliente, metodo, rota)

                self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)


class ReceitaApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=_usuario())

    def test_cadastro_rejeita_rendimento_igual_a_zero(self):
        resposta = self.client.post(
            "/api/producao/receitas/",
            {"nome": "Bolo", "rendimento_quantidade": "0"},
            format="json",
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rendimento_quantidade", resposta.data)

    def test_cadastro_exige_nome(self):
        resposta = self.client.post(
            "/api/producao/receitas/", {"rendimento_quantidade": "10"}, format="json"
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nome", resposta.data)

    def test_retorna_nao_encontrado_para_receita_inexistente(self):
        with patch.object(ReceitaViewSet, "get_object", side_effect=Http404):
            resposta = self.client.get("/api/producao/receitas/999/")

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_exclui_receita_sem_vinculos(self):
        receita = Mock()
        with patch.object(ReceitaViewSet, "get_object", return_value=receita):
            resposta = self.client.delete("/api/producao/receitas/1/")

        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
        receita.delete.assert_called_once()

    def test_nao_exclui_receita_vinculada_a_itens_de_pedido(self):
        receita = Mock()
        receita.delete.side_effect = ProtectedError("receita em uso", set())
        with patch.object(ReceitaViewSet, "get_object", return_value=receita):
            resposta = self.client.delete("/api/producao/receitas/1/")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("vinculada", str(resposta.data))


# ---------- complementos: lacunas encontradas na medicao de cobertura ----------

# evita abrir transacao real nos serializers que usam transaction.atomic
@contextmanager
def _sem_transacao():
    with patch.object(Atomic, "__enter__", return_value=None), patch.object(Atomic, "__exit__", return_value=False):
        yield


class ConcluirProducaoRepetidaTests(SimpleTestCase):
    def test_recusa_concluir_producao_ja_concluida_com_mensagem_propria(self):
        pedido = _pedido(Pedido.Status.PRODUCAO_CONCLUIDA)
        with _ambiente_conclusao(pedido) as amb:
            with self.assertRaises(ValidationError) as erro:
                concluir_producao(pedido, CONSUMO_PADRAO, DATA_VALIDADE)

        self.assertIn("já foi concluída", str(erro.exception.detail["status"]))
        amb.criar_lote.assert_not_called()
        pedido.save.assert_not_called()


class QuantidadePorPesoTests(SimpleTestCase):
    def test_usa_a_quantidade_em_peso_quando_o_item_nao_tem_unidades(self):
        ingrediente = _ingrediente()
        item = _item(receita=_receita("10"), quantidade=None, peso=Decimal("5.00"))
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO, itens=[item])

        with _composicao([_componente(ingrediente, "2.00")]):
            previstos, _, _ = _ingredientes_previstos(pedido)

        self.assertEqual(previstos[1]["necessario"], Decimal("1.00"))


class FaixasDeValidadeNaAnaliseTests(SimpleTestCase):
    HOJE = date(2026, 1, 1)

    def _alerta(self, dias):
        ingrediente = _ingrediente(saldo="5.00", validade=self.HOJE + timedelta(days=dias))
        previstos = {1: {"ingrediente": ingrediente, "necessario": Decimal("1.00")}}
        pedido = _pedido(Pedido.Status.PEDIDO_FEITO, itens=[_item(quantidade=2)])
        saldo = {"quantidade_solicitada": 2, "quantidade_disponivel": Decimal("0"), "disponivel": False, "encaminhar_para_producao": True}
        with (
            patch("producao.services._ingredientes_previstos", return_value=(previstos, [], [])),
            patch("producao.services.Estoque.objects.verificar_disponibilidade", return_value=saldo),
            patch("producao.services.timezone.localdate", return_value=self.HOJE),
        ):
            return analisar_pedido(pedido)["ingredientes"][0]["alerta_validade"]

    def test_limites_de_cada_nivel_de_alerta(self):
        # 0 dia ja e critico; 1 a 7 atencao; 8 a 15 preventivo; acima disso sem alerta
        casos = {0: "critico", 1: "atencao", 7: "atencao", 8: "preventivo", 15: "preventivo", 16: None}
        for dias, nivel in casos.items():
            with self.subTest(dias=dias):
                alerta = self._alerta(dias)
                self.assertEqual(alerta["nivel"] if alerta else None, nivel)


class ReceitaSerializerGravacaoTests(SimpleTestCase):
    def test_cria_receita_com_ingredientes_e_produtos_relacionados(self):
        receita = SimpleNamespace(pk=7)
        ingrediente = SimpleNamespace(pk=1)
        produto = SimpleNamespace(pk=3)
        dados = {
            "nome": "Bolo",
            "rendimento_quantidade": Decimal("10"),
            "composicao": [{"ingrediente": ingrediente, "quantidade_necessaria": Decimal("2.00")}],
            "produtos_relacionados": [{"produto": produto, "quantidade": Decimal("1"), "unidade_medida": "un"}],
        }

        with (
            _sem_transacao(),
            patch("producao.serializers.Receita.objects.create", return_value=receita) as criar_receita,
            patch("producao.serializers.IngredienteReceita.objects.create") as criar_composicao,
            patch("producao.serializers.ReceitaProduto.objects.update_or_create") as relacionar,
        ):
            resultado = ReceitaSerializer().create(dados)

        self.assertEqual(resultado, receita)
        criar_receita.assert_called_once_with(nome="Bolo", rendimento_quantidade=Decimal("10"))
        criar_composicao.assert_called_once_with(receita=receita, ingrediente=ingrediente, quantidade_necessaria=Decimal("2.00"))
        relacionar.assert_called_once_with(
            receita=receita, produto=produto, defaults={"quantidade": Decimal("1"), "unidade_medida": "un"}
        )

    def test_cria_receita_sem_relacoes_quando_nao_sao_enviadas(self):
        with (
            _sem_transacao(),
            patch("producao.serializers.Receita.objects.create", return_value=SimpleNamespace(pk=7)),
            patch("producao.serializers.IngredienteReceita.objects.create") as criar_composicao,
            patch("producao.serializers.ReceitaProduto.objects.update_or_create") as relacionar,
        ):
            ReceitaSerializer().create({"nome": "Bolo"})

        criar_composicao.assert_not_called()
        relacionar.assert_not_called()

    def test_atualizacao_preserva_relacoes_omitidas(self):
        instancia = SimpleNamespace(nome="Bolo", save=Mock())

        with (
            _sem_transacao(),
            patch("producao.serializers.IngredienteReceita.objects.filter") as composicao,
            patch("producao.serializers.ReceitaProduto.objects.filter") as relacao,
        ):
            resultado = ReceitaSerializer().update(instancia, {"nome": "Bolo de cenoura"})

        self.assertEqual(resultado.nome, "Bolo de cenoura")
        instancia.save.assert_called_once()
        composicao.assert_not_called()
        relacao.assert_not_called()

    def test_atualizacao_substitui_a_composicao_enviada(self):
        instancia = SimpleNamespace(nome="Bolo", save=Mock())
        ingrediente = SimpleNamespace(pk=2)

        with (
            _sem_transacao(),
            patch("producao.serializers.IngredienteReceita.objects.filter") as composicao,
            patch("producao.serializers.IngredienteReceita.objects.create") as criar_composicao,
        ):
            ReceitaSerializer().update(
                instancia, {"composicao": [{"ingrediente": ingrediente, "quantidade_necessaria": Decimal("1.00")}]}
            )

        composicao.assert_called_once_with(receita=instancia)
        composicao.return_value.delete.assert_called_once()
        criar_composicao.assert_called_once_with(receita=instancia, ingrediente=ingrediente, quantidade_necessaria=Decimal("1.00"))

    def test_atualizacao_remove_produtos_que_nao_foram_enviados(self):
        instancia = SimpleNamespace(nome="Bolo", save=Mock())
        produto = SimpleNamespace(pk=3)

        with (
            _sem_transacao(),
            patch("producao.serializers.ReceitaProduto.objects.filter") as relacao,
            patch("producao.serializers.ReceitaProduto.objects.update_or_create") as relacionar,
        ):
            ReceitaSerializer().update(
                instancia, {"produtos_relacionados": [{"produto": produto, "quantidade": Decimal("1")}]}
            )

        relacao.return_value.exclude.assert_called_once_with(produto_id__in=[3])
        relacao.return_value.exclude.return_value.delete.assert_called_once()
        relacionar.assert_called_once_with(receita=instancia, produto=produto, defaults={"quantidade": Decimal("1")})

    def test_lista_os_produtos_relacionados_da_receita(self):
        receita = SimpleNamespace(pk=7)

        with (
            patch("producao.serializers.ReceitaProduto.objects.filter") as relacao,
            patch("producao.serializers.ReceitaProdutoSerializer") as serializer,
        ):
            serializer.return_value.data = [{"produto": 3}]
            resultado = ReceitaSerializer().get_produtos(receita)

        relacao.assert_called_once_with(receita=receita)
        self.assertEqual(resultado, [{"produto": 3}])


class AnaliseProducaoSerializerTests(SimpleTestCase):
    def test_representacao_devolve_a_analise_do_pedido(self):
        pedido = SimpleNamespace(pk=1)

        with patch("producao.serializers.analisar_pedido", return_value={"ingredientes": []}) as analisar:
            resultado = AnaliseProducaoSerializer().to_representation({"pedido": pedido})

        analisar.assert_called_once_with(pedido)
        self.assertEqual(resultado, {"ingredientes": []})

# ---------- testes originais: movimentacao de producao ----------

class MovimentacaoProducaoTests(SimpleTestCase):
    def test_conclusao_baixa_consumo_e_recusa_repeticao(self):
        pedido = SimpleNamespace(pk=10, tipo=Pedido.Tipo.EXTERNO, status=Pedido.Status.EM_PRODUCAO, save=Mock())
        produto = SimpleNamespace(pk=3, receita=None)
        item = SimpleNamespace(produto=produto, produto_id=3, receita=None, quantidade=2, quantidade_peso=None)
        pedido.itens = SimpleNamespace(select_related=lambda *args: [item])
        ingrediente = SimpleNamespace(quantidade_disponivel=Decimal("4.00"), custo_unitario=Decimal("3.00"), save=Mock())
        with (
            patch.object(Atomic, "__enter__", return_value=None),
            patch.object(Atomic, "__exit__", return_value=False),
            patch("producao.services.Pedido.objects.select_for_update") as lock_pedido,
            patch("producao.services._ingredientes_previstos", return_value=({1: {}}, [], [])),
            patch("producao.services._consumos_confirmados", return_value=[(ingrediente, Decimal("1.50"))]),
            patch("producao.services.Estoque.objects.verificar_disponibilidade", return_value={"quantidade_disponivel": Decimal("0")}),
            patch("producao.services.Estoque.objects.create") as criar_lote,
        ):
            lock_pedido.return_value.get.return_value = pedido
            resultado = concluir_producao(pedido, [{"ingrediente_id": 1, "quantidade": Decimal("1.50")}], "2026-11-05")
            self.assertEqual(resultado["custo"], Decimal("4.50"))
            self.assertEqual(ingrediente.quantidade_disponivel, Decimal("2.50"))
            self.assertEqual(pedido.status, Pedido.Status.PRODUCAO_CONCLUIDA)
            ingrediente.save.assert_called_once_with(update_fields=["quantidade_disponivel"])
            pedido.save.assert_called_once_with(update_fields=["status"])
            criar_lote.assert_called_once_with(produto=produto, quantidade_disponivel=Decimal("2"), data_validade="2026-11-05", custo=Decimal("4.50"))
            with self.assertRaises(ValidationError):
                concluir_producao(pedido, [{"ingrediente_id": 1, "quantidade": Decimal("1.50")}], "2026-11-05")

    def test_cancelamento_registra_uma_vez_e_muda_status(self):
        pedido = SimpleNamespace(pk=11, status=Pedido.Status.PEDIDO_FEITO, save=lambda **kwargs: None)
        with (
            patch.object(Atomic, "__enter__", return_value=None),
            patch.object(Atomic, "__exit__", return_value=False),
            patch("producao.services.Pedido.objects.select_for_update") as lock_pedido,
            patch("producao.services.Cancelamento.objects.filter") as buscar_cancelamento,
            patch("producao.services.Cancelamento.objects.create") as criar_cancelamento,
            patch("producao.services._consumos_confirmados", return_value=[]),
        ):
            lock_pedido.return_value.get.return_value = pedido
            buscar_cancelamento.return_value.exists.return_value = False
            resultado, _ = cancelar_pedido(pedido, [], "descarte")
            self.assertEqual(resultado.status, Pedido.Status.CANCELADO)
            criar_cancelamento.assert_called_once()
            with self.assertRaises(ValidationError):
                cancelar_pedido(pedido, [], "descarte")
            criar_cancelamento.assert_called_once()