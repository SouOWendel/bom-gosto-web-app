from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db.transaction import Atomic
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from inventario.models import Ingrediente
from estoque.models import Estoque
from pedido.models import ItemPedido, Pedido, Produto, Receita, ReceitaProduto
from .models import IngredienteReceita
from usuario.models import Usuario
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


class SaldoCompartilhadoTests(SimpleTestCase):
    # dois itens do mesmo produto nao podem aproveitar o mesmo saldo pronto duas vezes
    def test_saldo_pronto_e_dividido_entre_itens_do_mesmo_produto(self):
        from .services import _saldo_restante

        reservado = {}
        with patch(
            "producao.services.Estoque.objects.verificar_disponibilidade",
            return_value={"quantidade_disponivel": Decimal("3")},
        ):
            self.assertEqual(_saldo_restante(7, Decimal("2"), reservado), Decimal("2"))
            self.assertEqual(_saldo_restante(7, Decimal("2"), reservado), Decimal("1"))
            self.assertEqual(_saldo_restante(7, Decimal("2"), reservado), Decimal("0"))


class CustoReceitaApiTests(APITestCase):
    def setUp(self):
        usuario = Usuario.objects.create_user(login="teste-receitas", password="senha-de-teste-123", primeiro_acesso=False)
        self.client.force_authenticate(user=usuario)
        self.farinha = Ingrediente.objects.create(nome="Farinha", unidade_medida="kg", custo_unitario=Decimal("6.00"))

    # o custo da receita e gravado ao salvar e acompanha mudancas no custo do insumo
    def test_custo_da_receita_e_calculado_e_atualizado(self):
        resposta = self.client.post(
            "/api/producao/receitas/",
            {"nome": "Massa", "rendimento_quantidade": "1.00", "ingredientes": [{"ingrediente": self.farinha.pk, "quantidade_necessaria": "0.50"}]},
            format="json",
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.data["custo_calculado"], "3.00")

        self.client.patch(f"/api/inventario/ingrediente/{self.farinha.pk}/", {"custo_unitario": "8.00"}, format="json")
        receita = self.client.get(f"/api/producao/receitas/{resposta.data['id_receita']}/")
        self.assertEqual(receita.data["custo_calculado"], "4.00")


class ProducaoComReceitasComplementaresTests(APITestCase):
    def setUp(self):
        usuario = Usuario.objects.create_user(login="teste-composicao", password="senha-de-teste-123", primeiro_acesso=False)
        self.client.force_authenticate(user=usuario)
        self.farinha = Ingrediente.objects.create(nome="Farinha", unidade_medida="kg", quantidade_disponivel=Decimal("10"), custo_unitario=Decimal("5.00"))
        self.leite = Ingrediente.objects.create(nome="Leite condensado", unidade_medida="lata", quantidade_disponivel=Decimal("10"), custo_unitario=Decimal("8.00"))
        # a massa rende 1 bolo; o recheio rende 2 kg e cada bolo leva 0,5 kg
        self.massa = Receita.objects.create(nome="Massa", rendimento_quantidade=Decimal("1"))
        IngredienteReceita.objects.create(receita=self.massa, ingrediente=self.farinha, quantidade_necessaria=Decimal("1"))
        self.recheio = Receita.objects.create(nome="Recheio", rendimento_quantidade=Decimal("2"))
        IngredienteReceita.objects.create(receita=self.recheio, ingrediente=self.leite, quantidade_necessaria=Decimal("2"))
        self.bolo = Produto.objects.create(nome="Bolo recheado", preco_venda=Decimal("80"), receita=self.massa)
        ReceitaProduto.objects.create(produto=self.bolo, receita=self.recheio, quantidade=Decimal("0.5"), unidade_medida="kg")

    def _pedido(self, **item):
        pedido = Pedido.objects.create(tipo=Pedido.Tipo.INTERNO)
        ItemPedido.objects.create(pedido=pedido, quantidade=2, preco_unitario=Decimal("0"), **item)
        return pedido

    # a previsao soma a receita principal e a complementar e agrupa por receita
    def test_analise_soma_receita_principal_e_complementar(self):
        pedido = self._pedido(produto=self.bolo)
        analise = self.client.post(f"/api/producao/pedidos/{pedido.pk}/validar/").data
        necessarios = {linha["nome"]: linha["necessario"] for linha in analise["ingredientes"]}
        self.assertEqual(necessarios, {"Farinha": Decimal("2.00"), "Leite condensado": Decimal("1.00")})
        grupos = {grupo["nome"]: [i["nome"] for i in grupo["ingredientes"]] for grupo in analise["receitas"]}
        self.assertEqual(grupos, {"Massa": ["Farinha"], "Recheio": ["Leite condensado"]})

    # a conclusao aceita consumos informados por receita e baixa a soma de cada insumo
    def test_conclusao_baixa_ingredientes_das_duas_receitas(self):
        pedido = self._pedido(produto=self.bolo)
        self.client.post(f"/api/producao/pedidos/{pedido.pk}/iniciar/")
        resposta = self.client.post(
            f"/api/producao/pedidos/{pedido.pk}/concluir/",
            {"data_validade": "2026-12-01", "consumos": [
                {"ingrediente_id": self.farinha.pk, "quantidade": "2.00"},
                {"ingrediente_id": self.leite.pk, "quantidade": "1.00"},
            ]},
            format="json",
        )
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.farinha.refresh_from_db()
        self.leite.refresh_from_db()
        self.assertEqual(self.farinha.quantidade_disponivel, Decimal("8.00"))
        self.assertEqual(self.leite.quantidade_disponivel, Decimal("9.00"))
        self.assertEqual(Estoque.objects.get(produto=self.bolo).quantidade_disponivel, Decimal("2.00"))

    # pedido antigo com receita no proprio item continua usando so aquela receita
    def test_item_antigo_com_receita_usa_somente_ela(self):
        pedido = self._pedido(receita=self.massa)
        analise = self.client.post(f"/api/producao/pedidos/{pedido.pk}/validar/").data
        self.assertEqual([linha["nome"] for linha in analise["ingredientes"]], ["Farinha"])

    # receita complementar sem ingredientes impede a producao e explica o motivo
    def test_complementar_sem_ingredientes_gera_ausencia(self):
        vazia = Receita.objects.create(nome="Cobertura", rendimento_quantidade=Decimal("1"))
        ReceitaProduto.objects.create(produto=self.bolo, receita=vazia, quantidade=Decimal("0.2"))
        pedido = self._pedido(produto=self.bolo)
        analise = self.client.post(f"/api/producao/pedidos/{pedido.pk}/validar/").data
        self.assertEqual([a["motivo"] for a in analise["ausencias"]], ["A receita Cobertura ainda não tem ingredientes."])

    # saldo pronto que chega depois do inicio nao some da lista usada no cancelamento (RF26)
    def test_cancelamento_lista_receitas_mesmo_com_estoque_pronto(self):
        pedido = Pedido.objects.create(tipo=Pedido.Tipo.EXTERNO, subtipo=Pedido.Subtipo.PERSONALIZADO, status=Pedido.Status.EM_PRODUCAO)
        ItemPedido.objects.create(pedido=pedido, produto=self.bolo, quantidade=1, preco_unitario=Decimal("80"))
        Estoque.objects.create(produto=self.bolo, quantidade_disponivel=Decimal("1"))
        analise = self.client.post(f"/api/producao/pedidos/{pedido.pk}/validar/").data
        self.assertEqual(analise["ingredientes"], [])
        nomes = {linha["nome"]: linha["necessario"] for linha in analise["ingredientes_receitas"]}
        self.assertEqual(nomes, {"Farinha": Decimal("1.00"), "Leite condensado": Decimal("0.50")})
