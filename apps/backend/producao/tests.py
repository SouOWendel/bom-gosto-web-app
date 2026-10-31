from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db.transaction import Atomic
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from pedido.models import Pedido
from .services import cancelar_pedido, concluir_producao


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
