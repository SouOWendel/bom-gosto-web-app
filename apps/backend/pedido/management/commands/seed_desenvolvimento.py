from datetime import date, time, timedelta
from decimal import Decimal
import secrets

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from estoque.models import Estoque
from inventario.models import Ingrediente
from pedido.models import Cancelamento, Cliente, ItemPedido, Pedido, Produto, Receita, ReceitaProduto
from producao.models import IngredienteReceita
from producao.services import recalcular_custo_receita
from usuario.models import Usuario

# carrega os dados de exemplo na mesma ordem do fluxo da confeitaria:
#   1. inventario (ingredientes)
#   2. receitas (ficha tecnica com ingredientes do inventario)
#   3. produtos (itens vendaveis ligados a uma receita)
#   4. estoque (lotes de produto pronto na vitrine)
#   5. pedidos (historico e roteiro de demonstracao)
# cada etapa depende apenas das anteriores; tudo roda em uma transacao
# o comando e idempotente: registros sao localizados pelo nome/contato e atualizados
# sem --resetar-demo, saldos, lotes e pedidos do roteiro ja movimentados sao preservados


# nome, unidade, quantidade, custo unitario, dias para vencer, quantidade minima
# as validades cobrem os tres niveis do semaforo (RN17) e ha insumos abaixo do minimo
INGREDIENTES = [
    ("Farinha de trigo", "kg", "5.00", "4.50", 60, "2.00"),
    ("Açúcar refinado", "kg", "3.00", "5.00", 14, "1.00"),
    ("Manteiga", "kg", "1.50", "40.00", 6, "0.50"),
    ("Chocolate em pó", "kg", "1.00", "30.00", 5, "0.50"),
    ("Ovos", "un", "30.00", "0.80", 12, "12.00"),
    ("Leite condensado", "lata", "8.00", "7.50", 90, "4.00"),
    ("Creme de leite", "caixa", "4.00", "4.20", -1, "2.00"),
    ("Leite integral", "L", "2.00", "5.50", 0, "2.00"),
    ("Banana prata", "kg", "2.00", "6.00", 3, "1.00"),
    ("Queijo meia cura", "kg", "0.30", "45.00", 20, "1.00"),
    ("Coco ralado", "kg", "0.50", "28.00", 40, "0.20"),
]

# nome, rendimento, composicao [(ingrediente, quantidade na unidade do inventario)]
RECEITAS = [
    ("Massa branca", "1.00", [("Farinha de trigo", "1.00"), ("Açúcar refinado", "0.50"), ("Manteiga", "0.20"), ("Ovos", "4.00")]),
    ("Recheio de beijinho", "1.00", [("Leite condensado", "2.00"), ("Coco ralado", "0.10"), ("Manteiga", "0.03")]),
    ("Recheio delícia de limão", "1.00", [("Leite condensado", "2.00"), ("Creme de leite", "1.00")]),
    ("Brigadeiro tradicional", "50.00", [("Leite condensado", "2.00"), ("Chocolate em pó", "0.10"), ("Manteiga", "0.05")]),
    ("Bolinha de queijo", "50.00", [("Farinha de trigo", "0.50"), ("Queijo meia cura", "0.40"), ("Leite integral", "1.00"), ("Ovos", "2.00")]),
    ("Caseirinho vulcão", "6.00", [("Farinha de trigo", "0.60"), ("Chocolate em pó", "0.30"), ("Açúcar refinado", "0.40"), ("Ovos", "6.00"), ("Leite condensado", "2.00")]),
    ("Banoffee de pote", "10.00", [("Banana prata", "1.50"), ("Leite condensado", "2.00"), ("Creme de leite", "2.00"), ("Açúcar refinado", "0.20")]),
]

# nome, preco de venda, receita principal (None para itens de revenda/brinde)
PRODUTOS = [
    ("Bolo 1kg massa branca", "80.90", "Massa branca"),
    ("Caseirinho", "40.00", "Caseirinho vulcão"),
    ("Salgado bolinha de queijo", "0.90", "Bolinha de queijo"),
    ("Doce", "1.40", "Brigadeiro tradicional"),
    ("Topper simples", "8.00", None),
    ("Refrigerante", "9.00", None),
    ("Pote", "15.00", "Banoffee de pote"),
    ("Fatia", "41.20", "Massa branca"),
    ("Mini vulcão", "20.00", "Caseirinho vulcão"),
    ("Bolo 1kg delícia de limão", "95.00", "Massa branca"),
    ("Bolo 1kg beijinho", "95.00", "Massa branca"),
]

# produto, receita complementar, quantidade por unidade do produto (na unidade do rendimento), unidade
# a massa vem da receita principal; o recheio entra como receita complementar (RF18)
RECEITAS_COMPLEMENTARES = [
    ("Bolo 1kg delícia de limão", "Recheio delícia de limão", "0.40", "kg"),
    ("Bolo 1kg beijinho", "Recheio de beijinho", "0.40", "kg"),
]

# produto, quantidade, dias para vencer, custo do lote
# o bolo do roteiro fica sem saldo para que o pedido seja encaminhado a Producao (RN06)
LOTES = [
    ("Doce", "40.00", 2, "18.00"),
    ("Salgado bolinha de queijo", "30.00", 0, "12.00"),
    ("Fatia", "4.00", 10, "36.00"),
    ("Refrigerante", "12.00", 120, "60.00"),
]

CLIENTES = [
    ("Licilene Alves", "(11) 97654-3210", "Rua das Acácias, 120"),
    ("Natália", "(11) 98123-1485", "Av. Brasil, 845"),
    ("Vivi", "(11) 97456-1003", "Rua Santa Clara, 33"),
    ("Joseane", "(11) 98765-4321", "Rua Alberto Borges Soveral, 50"),
    ("Márcia Regina", "(11) 99321-1358", "Rua do Comércio, 77"),
    ("Rafaela Souza", "(11) 96543-2201", "Rua Paraná, 410"),
    ("Carlos Menezes", "(11) 94567-8890", "Av. Independência, 1500"),
]

# pedidos ja encerrados, adaptados de `database/insert_data.sql`
# cliente, data, horario, total, sinal, status, itens [(produto, qtd, recheio, decoracao, peso)]
PEDIDOS_HISTORICOS = [
    ("Licilene Alves", date(2026, 9, 26), time(17, 30), "120.90", "60.45", Pedido.Status.CONCLUIDO,
     [("Bolo 1kg massa branca", 1, "delícia de limão", "Decoração (R$ 40,00)", "1.00")]),
    ("Natália", date(2026, 9, 22), time(14, 0), "40.00", "0.00", Pedido.Status.CONCLUIDO,
     [("Caseirinho", 1, "vulcão formigueiro", None, "1.00")]),
    ("Vivi", date(2026, 9, 19), time(16, 0), "162.63", "0.00", Pedido.Status.CONCLUIDO,
     [("Bolo 1kg massa branca", 1, "beijinho", "feliz aniversário mãe (bolo rosa)", "1.00"),
      ("Salgado bolinha de queijo", 50, None, None, None), ("Doce", 25, "brigadeiro", None, None),
      ("Topper simples", 1, None, "brinde", None), ("Refrigerante", 1, None, "brinde", None)]),
    ("Joseane", date(2026, 9, 5), time(11, 0), "51.00", "25.50", Pedido.Status.CONCLUIDO,
     [("Pote", 2, "brigadeiro", None, None), ("Pote", 1, "bannoffe", None, None)]),
    ("Márcia Regina", date(2026, 9, 4), time(10, 0), "61.20", "0.00", Pedido.Status.CONCLUIDO,
     [("Fatia", 1, "Matilda", None, "1.00"), ("Mini vulcão", 1, "ninho", None, "1.00")]),
    ("Rafaela Souza", date(2026, 9, 12), time(15, 0), "115.90", "57.95", Pedido.Status.CANCELADO,
     [("Bolo 1kg massa branca", 1, "brigadeiro", "Parabéns (R$ 35,00)", "1.00")]),
]

# Iniciar a produção marca o sinal como pago (regra provisória do MVP; ver RN13).
# Pedidos que já passaram desse ponto entram no seed com o sinal pago.
STATUS_COM_SINAL_PAGO = {
    Pedido.Status.EM_PRODUCAO,
    Pedido.Status.PRODUCAO_CONCLUIDA,
    Pedido.Status.CONCLUIDO,
}


def _sinal_pago(tipo, sinal, status):
    return tipo == Pedido.Tipo.EXTERNO and Decimal(sinal) > 0 and status in STATUS_COM_SINAL_PAGO


class Command(BaseCommand):
    help = "Carrega dados de exemplo seguindo o fluxo Inventário → Receitas → Produtos → Estoque → Pedidos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--resetar-demo",
            action="store_true",
            help="Restaura insumos, lotes e pedidos do roteiro; remove cancelamentos e produtos reaproveitados (sem receita e sem pedidos).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        hoje = timezone.localdate()
        resetar = options.get("resetar_demo", False)

        ingredientes = self._carregar_ingredientes(hoje, resetar)
        receitas = self._carregar_receitas(ingredientes)
        produtos = self._carregar_produtos(receitas)
        self._carregar_lotes(produtos, hoje, resetar)
        clientes = self._carregar_clientes()
        self._carregar_pedidos_historicos(clientes, produtos)
        self._carregar_pedidos_demo(clientes, produtos, hoje, resetar)
        self._carregar_usuario()

        self.stdout.write(self.style.SUCCESS(
            f"Dados de exemplo carregados: {len(ingredientes)} ingredientes, {len(receitas)} receitas, "
            f"{len(produtos)} produtos, {len(LOTES)} lotes e {len(PEDIDOS_HISTORICOS)} pedidos históricos."
        ))

    # 1. Inventario: sem --resetar-demo, saldos ja consumidos em ensaios anteriores sao preservados
    def _carregar_ingredientes(self, hoje, resetar):
        ingredientes = {}
        for nome, unidade, quantidade, custo, dias, minimo in INGREDIENTES:
            valores = {
                "unidade_medida": unidade,
                "quantidade_disponivel": Decimal(quantidade),
                "custo_unitario": Decimal(custo),
                "data_validade": hoje + timedelta(days=dias),
                "quantidade_minima": Decimal(minimo),
            }
            ingrediente = Ingrediente.objects.filter(nome=nome).order_by("id_ingrediente").first()
            if ingrediente is None:
                ingrediente = Ingrediente.objects.create(nome=nome, **valores)
            elif resetar:
                for campo, valor in valores.items():
                    setattr(ingrediente, campo, valor)
                ingrediente.save()
            elif ingrediente.unidade_medida != unidade:
                # a unidade nao depende do ensaio; corrige registros antigos sem resetar saldos
                ingrediente.unidade_medida = unidade
                ingrediente.save(update_fields=["unidade_medida"])
            ingredientes[nome] = ingrediente
        return ingredientes

    # 2. Receitas: grava a ficha tecnica e calcula o custo pelo mesmo servico usado na API
    def _carregar_receitas(self, ingredientes):
        receitas = {}
        for nome, rendimento, composicao in RECEITAS:
            receita, _ = Receita.objects.update_or_create(
                nome=nome,
                defaults={"rendimento_quantidade": Decimal(rendimento)},
            )
            usados = []
            for ingrediente_nome, quantidade in composicao:
                ingrediente = ingredientes[ingrediente_nome]
                IngredienteReceita.objects.update_or_create(
                    receita=receita,
                    ingrediente=ingrediente,
                    defaults={"quantidade_necessaria": Decimal(quantidade)},
                )
                usados.append(ingrediente.pk)
            IngredienteReceita.objects.filter(receita=receita).exclude(ingrediente_id__in=usados).delete()
            recalcular_custo_receita(receita)
            receitas[nome] = receita
        return receitas

    # 3. Produtos: cada item vendavel aponta para a receita usada na Producao
    def _carregar_produtos(self, receitas):
        produtos = {}
        for nome, preco, receita_nome in PRODUTOS:
            produto, _ = Produto.objects.update_or_create(
                nome=nome,
                defaults={
                    "preco_venda": Decimal(preco),
                    "receita": receitas[receita_nome] if receita_nome else None,
                },
            )
            produtos[nome] = produto
        for produto_nome, receita_nome, quantidade, unidade in RECEITAS_COMPLEMENTARES:
            ReceitaProduto.objects.update_or_create(
                produto=produtos[produto_nome],
                receita=receitas[receita_nome],
                defaults={"quantidade": Decimal(quantidade), "unidade_medida": unidade},
            )
        return produtos

    # 4. Estoque: lotes de vitrine com alertas de validade variados
    def _carregar_lotes(self, produtos, hoje, resetar):
        if resetar:
            Estoque.objects.filter(produto__in=produtos.values()).delete()
            # produtos criados por cancelamentos com reaproveitamento (RN12) nao tem receita
            # nem pedidos; sao removidos para que cada ensaio comece do mesmo estado
            reaproveitados = Produto.objects.filter(receita__isnull=True, itens_pedido__isnull=True).exclude(
                pk__in=[produto.pk for produto in produtos.values()]
            )
            Estoque.objects.filter(produto__in=reaproveitados).delete()
            reaproveitados.delete()
        for produto_nome, quantidade, dias, custo in LOTES:
            produto = produtos[produto_nome]
            if Estoque.objects.filter(produto=produto).exists():
                continue
            Estoque.objects.create(
                produto=produto,
                quantidade_disponivel=Decimal(quantidade),
                data_validade=hoje + timedelta(days=dias),
                custo=Decimal(custo),
            )
        if Estoque.objects.filter(produto=produtos["Bolo 1kg delícia de limão"], quantidade_disponivel__gt=0).exists():
            self.stdout.write(self.style.WARNING(
                "Há saldo de 'Bolo 1kg delícia de limão' no estoque; o pedido do roteiro não irá para Produção. "
                "Use --resetar-demo para limpar os lotes de ensaio."
            ))

    # 5a. Clientes: o telefone identifica o cadastro, como na criacao de pedidos pela API
    def _carregar_clientes(self):
        clientes = {}
        for nome, telefone, endereco in CLIENTES:
            cliente, _ = Cliente.objects.update_or_create(
                telefone=telefone,
                defaults={"nome": nome, "endereco": endereco},
            )
            clientes[nome] = cliente
        return clientes

    # 5b. Pedidos historicos: ja encerrados, nao movimentam inventario nem estoque
    def _carregar_pedidos_historicos(self, clientes, produtos):
        for nome, data_entrega, horario, total, sinal, status, itens in PEDIDOS_HISTORICOS:
            cliente = clientes[nome]
            pedido, _ = Pedido.objects.update_or_create(
                cliente=cliente,
                data_entrega=data_entrega,
                horario_entrega=horario,
                defaults={
                    "tipo": Pedido.Tipo.EXTERNO,
                    "subtipo": Pedido.Subtipo.PERSONALIZADO,
                    "status": status,
                    "valor_total": Decimal(total),
                    "valor_sinal": Decimal(sinal),
                    "sinal_pago": _sinal_pago(Pedido.Tipo.EXTERNO, sinal, status),
                    "endereco_entrega": cliente.endereco,
                    "forma_pagamento": "pix",
                },
            )
            self._substituir_itens(pedido, produtos, itens)
            # todo pedido cancelado tem o registro correspondente em /api/cancelamento/
            if status == Pedido.Status.CANCELADO:
                Cancelamento.objects.get_or_create(
                    pedido=pedido,
                    defaults={"destino": "descarte", "data_cancelamento": data_entrega},
                )

    # 5c. Pedidos do roteiro de demonstracao, um para cada caminho do fluxo
    # sem --resetar-demo, o andamento de um ensaio anterior e preservado
    def _carregar_pedidos_demo(self, clientes, produtos, hoje, resetar):
        # cliente (None = reposicao interna), tipo, subtipo, entrega, horario, total, sinal, status, itens
        demos = [
            # encomenda sem produto pronto: Pedidos -> Producao (massa + recheio) -> Estoque -> entrega
            ("Licilene Alves", Pedido.Tipo.EXTERNO, Pedido.Subtipo.PERSONALIZADO, hoje + timedelta(days=2), time(15, 0),
             "120.90", "60.45", Pedido.Status.PEDIDO_FEITO,
             [("Bolo 1kg delícia de limão", 1, None, "Feliz aniversário", "1.00")]),
            # encomenda ja em producao que pode ser cancelada com reaproveitamento (RN12)
            ("Carlos Menezes", Pedido.Tipo.EXTERNO, Pedido.Subtipo.PERSONALIZADO, hoje + timedelta(days=1), time(15, 0),
             "90.00", "45.00", Pedido.Status.EM_PRODUCAO,
             [("Mini vulcão", 3, "ninho", None, None), ("Pote", 2, "bannoffe", None, None)]),
            # venda de vitrine atendida direto pelo estoque (consumir-estoque)
            ("Natália", Pedido.Tipo.EXTERNO, Pedido.Subtipo.VITRINE, hoje, time(10, 30),
             "55.20", "0.00", Pedido.Status.PEDIDO_FEITO,
             [("Doce", 10, None, None, None), ("Fatia", 1, None, None, None)]),
            # reposicao interna da vitrine: Producao gera lote e o pedido e concluido
            (None, Pedido.Tipo.INTERNO, None, hoje + timedelta(days=1), time(8, 0),
             "0.00", "0.00", Pedido.Status.PEDIDO_FEITO,
             [("Doce", 50, None, None, None)]),
        ]
        for nome, tipo, subtipo, data_entrega, horario, total, sinal, status, itens in demos:
            cliente = clientes[nome] if nome else None
            pedido = (
                Pedido.objects.filter(cliente=cliente, tipo=tipo, subtipo=subtipo, horario_entrega=horario)
                .order_by("id_pedido")
                .first()
            )
            if pedido is not None and not resetar:
                continue
            if pedido is None:
                pedido = Pedido(cliente=cliente, tipo=tipo, subtipo=subtipo, horario_entrega=horario)
            else:
                Cancelamento.objects.filter(pedido=pedido).delete()
            pedido.status = status
            pedido.data_entrega = data_entrega
            pedido.valor_total = Decimal(total)
            pedido.valor_sinal = Decimal(sinal)
            # O reset volta o pedido ao status do roteiro; o sinal pago de um ensaio anterior sai junto.
            pedido.sinal_pago = _sinal_pago(tipo, sinal, status)
            pedido.endereco_entrega = cliente.endereco if cliente else None
            pedido.forma_pagamento = "pix" if cliente else None
            pedido.save()
            self._substituir_itens(pedido, produtos, itens)

    # substitui os itens para evitar duplicatas ou itens antigos ao repetir o seed
    def _substituir_itens(self, pedido, produtos, itens):
        pedido.itens.all().delete()
        for produto_nome, quantidade, recheio, decoracao, peso in itens:
            produto = produtos[produto_nome]
            ItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                quantidade=quantidade,
                preco_unitario=produto.preco_venda,
                custo_unitario=self._custo_unitario(produto),
                recheio=recheio,
                decoracao=decoracao,
                quantidade_peso=Decimal(peso) if peso else None,
            )

    # custo de referencia por unidade: receita principal mais as complementares (RF18),
    # na mesma proporcao usada pela Producao
    def _custo_unitario(self, produto):
        partes = []
        if produto.receita is not None:
            partes.append((produto.receita, Decimal("1")))
        partes.extend(
            (relacao.receita, relacao.quantidade)
            for relacao in ReceitaProduto.objects.filter(produto=produto).exclude(receita_id=produto.receita_id).select_related("receita")
        )
        if not partes or any(not receita.rendimento_quantidade for receita, _ in partes):
            return None
        custo = sum(
            (receita.custo_calculado * por_unidade / receita.rendimento_quantidade for receita, por_unidade in partes),
            Decimal("0"),
        )
        return custo.quantize(Decimal("0.01"))

    # a senha temporaria so e exibida quando o usuario de exemplo e criado pela primeira vez
    def _carregar_usuario(self):
        usuario, criado = Usuario.objects.get_or_create(
            login="confeiteira",
            defaults={"primeiro_acesso": True},
        )
        if criado:
            senha_temporaria = str(secrets.randbelow(900000) + 100000)
            usuario.set_password(senha_temporaria)
            usuario.save(update_fields=["password"])
            self.stdout.write(self.style.WARNING(
                f"Login de exemplo: confeiteira | senha temporária: {senha_temporaria}"
            ))
        else:
            self.stdout.write("Usuário de exemplo existente; senha não foi alterada.")
