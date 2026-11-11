from datetime import date, time, timedelta
from decimal import Decimal
import secrets

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from estoque.models import Estoque
from inventario.models import Ingrediente
from pedido.models import Cancelamento, Cliente, ItemPedido, Pedido, Produto, Receita
from producao.models import IngredienteReceita
from usuario.models import Usuario

# carrega em uma transacao Clientes, Receitas, Produtos, Pedidos e Itens de exemplo
# adapta os dados de `database/insert_data.sql`
# tabelas sao atualizadas com `update_or_create`
# os itens dos pedidos sao substituidos e o usuario de exemplo so é criado se faltar
# a senha temporaria so é exibida quando o usuario de exemplo é criado pela primeira vez
# tambem prepara ingredientes, composicao das receitas, lotes e os pedidos do roteiro de demonstracao
class Command(BaseCommand):
    help = "Carrega dados de exemplo e prepara o roteiro de demonstração."

    def add_arguments(self, parser):
        parser.add_argument(
            "--resetar-demo",
            action="store_true",
            help="Restaura insumos, lotes e pedidos do roteiro; remove cancelamentos e produtos reaproveitados (sem receita e sem pedidos).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        hoje = timezone.localdate()
        clientes_dados = [
            ("Licilene Alves", "(11) 97654-3210", "Rua das Acácias, 120"),
            ("Natália", "(11) 98123-1485", "Av. Brasil, 845"),
            ("Vivi", "(11) 97456-1003", "Rua Santa Clara, 33"),
            ("Joseane", "(11) 98765-4321", "Rua Alberto Borges Soveral, 50"),
            ("Márcia Regina", "(11) 99321-1358", "Rua do Comércio, 77"),
            ("Rafaela Souza", "(11) 96543-2201", "Rua Paraná, 410"),
            ("Carlos Menezes", "(11) 94567-8890", "Av. Independência, 1500"),
        ]
        clientes = {}
        for nome, telefone, endereco in clientes_dados:
            cliente, _ = Cliente.objects.update_or_create(
                telefone=telefone,
                defaults={"nome": nome, "endereco": endereco},
            )
            clientes[nome] = cliente

        receitas_dados = [
            ("Massa branca", "1.00"),
            ("Recheio de beijinho", "1.00"),
            ("Recheio delícia de limão", "1.00"),
            ("Brigadeiro tradicional", "50.00"),
            ("Bolinha de queijo", "50.00"),
            ("Caseirinho vulcão", "6.00"),
            ("Banoffee de pote", "10.00"),
        ]
        receitas = {}
        for nome, rendimento in receitas_dados:
            receita, _ = Receita.objects.update_or_create(
                nome=nome,
                defaults={"rendimento_quantidade": Decimal(rendimento)},
            )
            receitas[nome] = receita

        produtos_dados = [
            ("Bolo 1kg massa branca", "80.90", "Massa branca"),
            ("Caseirinho", "40.00", "Caseirinho vulcão"),
            ("Salgado bolinha de queijo", "0.90", "Bolinha de queijo"),
            ("Doce", "1.40", "Brigadeiro tradicional"),
            ("Topper simples", "8.00", None),
            ("Refrigerante", "9.00", None),
            ("Pote", "15.00", "Banoffee de pote"),
            ("Fatia", "41.20", "Massa branca"),
            ("Mini vulcão", "20.00", "Caseirinho vulcão"),
        ]
        produtos = {}
        for nome, preco, receita_nome in produtos_dados:
            produto, _ = Produto.objects.update_or_create(
                nome=nome,
                defaults={
                    "preco_venda": Decimal(preco),
                    "receita": receitas.get(receita_nome),
                },
            )
            produtos[nome] = produto

        pedidos_dados = [
            ("Licilene Alves", date(2026, 9, 26), time(17, 30), "120.90", "60.45", Pedido.Status.CONCLUIDO, [("Bolo 1kg massa branca", 1, "delícia de limão", "Decoração (R$ 40,00)", "1.00")]),
            ("Natália", date(2026, 9, 22), time(14, 0), "40.00", "0.00", Pedido.Status.CONCLUIDO, [("Caseirinho", 1, "vulcão formigueiro", None, "1.00")]),
            ("Vivi", date(2026, 9, 19), time(16, 0), "162.63", "0.00", Pedido.Status.CONCLUIDO, [("Bolo 1kg massa branca", 1, "beijinho", "feliz aniversário mãe (bolo rosa)", "1.00"), ("Salgado bolinha de queijo", 50, None, None, None), ("Doce", 25, "brigadeiro", None, None), ("Topper simples", 1, None, "brinde", None), ("Refrigerante", 1, None, "brinde", None)]),
            ("Joseane", date(2026, 9, 5), time(11, 0), "51.00", "25.50", Pedido.Status.CONCLUIDO, [("Pote", 2, "brigadeiro", None, None), ("Pote", 1, "bannoffe", None, None)]),
            ("Márcia Regina", date(2026, 9, 4), time(10, 0), "61.20", "0.00", Pedido.Status.CONCLUIDO, [("Fatia", 1, "Matilda", None, "1.00"), ("Mini vulcão", 1, "ninho", None, "1.00")]),
            ("Rafaela Souza", date(2026, 9, 12), time(15, 0), "115.90", "57.95", Pedido.Status.CANCELADO, [("Bolo 1kg massa branca", 1, "brigadeiro", "Parabéns (R$ 35,00)", "1.00")]),
        ]

        for (nome, data_entrega, horario, total, sinal, status,
             itens_dados) in pedidos_dados:
            pedido, _ = Pedido.objects.update_or_create(
                cliente=clientes[nome],
                data_entrega=data_entrega,
                horario_entrega=horario,
                defaults={
                    "tipo": Pedido.Tipo.EXTERNO,
                    "subtipo": Pedido.Subtipo.PERSONALIZADO,
                    "status": status,
                    "valor_total": Decimal(total),
                    "valor_sinal": Decimal(sinal),
                    "endereco_entrega": clientes[nome].endereco,
                    "forma_pagamento": "pix",
                },
            )
            # substitui os itens para evitar duplicatas ou itens antigos ao repetir o seed
            pedido.itens.all().delete()
            for produto_nome, quantidade, recheio, decoracao, peso in itens_dados:
                ItemPedido.objects.create(
                    pedido=pedido,
                    produto=produtos[produto_nome],
                    quantidade=quantidade,
                    preco_unitario=produtos[produto_nome].preco_venda,
                    recheio=recheio,
                    decoracao=decoracao,
                    quantidade_peso=Decimal(peso) if peso else None,
                )

        resetar = options.get("resetar_demo", False)
        ingredientes = self._carregar_ingredientes(hoje, resetar)
        self._carregar_composicoes(receitas, ingredientes)
        self._carregar_lotes(produtos, hoje, resetar)
        self._carregar_pedidos_demo(clientes, produtos, hoje, resetar)

        usuario, criado = Usuario.objects.get_or_create(
            login="confeiteira",
            defaults={"primeiro_acesso": True},
        )
        if criado:
            senha_temporaria = str(secrets.randbelow(900000) + 100000)
            usuario.set_password(senha_temporaria)
            usuario.save(update_fields=["password"])
            self.stdout.write(
                self.style.WARNING(
                    f"Login de exemplo: confeiteira | senha temporária: {senha_temporaria}"
                )
            )
        else:
            self.stdout.write("Usuário de exemplo existente; senha não foi alterada.")

        self.stdout.write(self.style.SUCCESS("Dados de exemplo carregados/atualizados."))

    # cria os insumos com validades que cobrem os tres niveis do semaforo (RN17)
    # sem --resetar-demo, saldos ja consumidos em ensaios anteriores sao preservados
    def _carregar_ingredientes(self, hoje, resetar):
        # nome, unidade, quantidade, custo unitario, dias para vencer, quantidade minima
        dados = [
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
        ingredientes = {}
        for nome, unidade, quantidade, custo, dias, minimo in dados:
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

    # define a ficha tecnica de cada receita e o custo de referencia
    def _carregar_composicoes(self, receitas, ingredientes):
        composicoes = {
            "Massa branca": [("Farinha de trigo", "1.00"), ("Açúcar refinado", "0.50"), ("Manteiga", "0.20"), ("Ovos", "4.00")],
            "Recheio de beijinho": [("Leite condensado", "2.00"), ("Coco ralado", "0.10"), ("Manteiga", "0.03")],
            "Recheio delícia de limão": [("Leite condensado", "2.00"), ("Creme de leite", "1.00")],
            "Brigadeiro tradicional": [("Leite condensado", "2.00"), ("Chocolate em pó", "0.10"), ("Manteiga", "0.05")],
            "Bolinha de queijo": [("Farinha de trigo", "0.50"), ("Queijo meia cura", "0.40"), ("Leite integral", "1.00"), ("Ovos", "2.00")],
            "Caseirinho vulcão": [("Farinha de trigo", "0.60"), ("Chocolate em pó", "0.30"), ("Açúcar refinado", "0.40"), ("Ovos", "6.00"), ("Leite condensado", "2.00")],
            "Banoffee de pote": [("Banana prata", "1.50"), ("Leite condensado", "2.00"), ("Creme de leite", "2.00"), ("Açúcar refinado", "0.20")],
        }
        for receita_nome, linhas in composicoes.items():
            receita = receitas[receita_nome]
            usados = []
            custo = Decimal("0")
            for ingrediente_nome, quantidade in linhas:
                ingrediente = ingredientes[ingrediente_nome]
                IngredienteReceita.objects.update_or_create(
                    receita=receita,
                    ingrediente=ingrediente,
                    defaults={"quantidade_necessaria": Decimal(quantidade)},
                )
                usados.append(ingrediente.pk)
                custo += Decimal(quantidade) * (ingrediente.custo_unitario or Decimal("0"))
            IngredienteReceita.objects.filter(receita=receita).exclude(ingrediente_id__in=usados).delete()
            receita.custo_calculado = custo.quantize(Decimal("0.01"))
            receita.save(update_fields=["custo_calculado"])

    # cria lotes de vitrine com alertas variados; o bolo do roteiro fica sem saldo
    # para que o pedido seja encaminhado a Producao (RN06)
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
        # produto, quantidade, dias para vencer, custo do lote
        lotes = [
            ("Doce", "40.00", 2, "18.00"),
            ("Salgado bolinha de queijo", "30.00", 0, "12.00"),
            ("Fatia", "4.00", 10, "36.00"),
            ("Refrigerante", "12.00", 120, "60.00"),
        ]
        for produto_nome, quantidade, dias, custo in lotes:
            produto = produtos[produto_nome]
            if Estoque.objects.filter(produto=produto).exists():
                continue
            Estoque.objects.create(
                produto=produto,
                quantidade_disponivel=Decimal(quantidade),
                data_validade=hoje + timedelta(days=dias),
                custo=Decimal(custo),
            )
        saldo_bolo = sum(
            (lote.quantidade_disponivel for lote in Estoque.objects.filter(produto=produtos["Bolo 1kg massa branca"])),
            Decimal("0"),
        )
        if saldo_bolo > 0:
            self.stdout.write(self.style.WARNING(
                "Há saldo de 'Bolo 1kg massa branca' no estoque; o pedido do roteiro não irá para Produção. "
                "Use --resetar-demo para limpar os lotes de ensaio."
            ))

    # prepara os pedidos usados nos passos 3 a 6 do roteiro
    # sem --resetar-demo, o andamento de um ensaio anterior e preservado
    def _carregar_pedidos_demo(self, clientes, produtos, hoje, resetar):
        demos = [
            # Passos 3 a 5: encomenda nova que segue para Produção
            ("Licilene Alves", hoje + timedelta(days=2), time(15, 0), "120.90", "60.45", Pedido.Status.PEDIDO_FEITO,
             [("Bolo 1kg massa branca", 1, "delícia de limão", "Feliz aniversário", "1.00")]),
            # Passo 6: encomenda já em produção que será cancelada com reaproveitamento
            ("Carlos Menezes", hoje + timedelta(days=1), time(15, 0), "90.00", "45.00", Pedido.Status.EM_PRODUCAO,
             [("Mini vulcão", 3, "ninho", None, None), ("Pote", 2, "bannoffe", None, None)]),
        ]
        for nome, data_entrega, horario, total, sinal, status, itens_dados in demos:
            cliente = clientes[nome]
            pedido = (
                Pedido.objects.filter(cliente=cliente, horario_entrega=horario, tipo=Pedido.Tipo.EXTERNO)
                .order_by("id_pedido")
                .first()
            )
            if pedido is not None and not resetar:
                continue
            if pedido is None:
                pedido = Pedido(cliente=cliente, horario_entrega=horario)
            else:
                Cancelamento.objects.filter(pedido=pedido).delete()
            pedido.tipo = Pedido.Tipo.EXTERNO
            pedido.subtipo = Pedido.Subtipo.PERSONALIZADO
            pedido.status = status
            pedido.data_entrega = data_entrega
            pedido.valor_total = Decimal(total)
            pedido.valor_sinal = Decimal(sinal)
            pedido.endereco_entrega = cliente.endereco
            pedido.forma_pagamento = "pix"
            pedido.save()
            pedido.itens.all().delete()
            for produto_nome, quantidade, recheio, decoracao, peso in itens_dados:
                ItemPedido.objects.create(
                    pedido=pedido,
                    produto=produtos[produto_nome],
                    quantidade=quantidade,
                    preco_unitario=produtos[produto_nome].preco_venda,
                    recheio=recheio,
                    decoracao=decoracao,
                    quantidade_peso=Decimal(peso) if peso else None,
                )
