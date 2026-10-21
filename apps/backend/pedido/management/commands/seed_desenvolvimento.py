from datetime import date, time
from decimal import Decimal
import secrets

from django.core.management.base import BaseCommand
from django.db import transaction

from pedido.models import Cliente, ItemPedido, Pedido, Produto, Receita
from usuario.models import Usuario

# carrega em uma transacao Clientes, Receitas, Produtos, Pedidos e Itens de exemplo
# adapta os dados de `database/insert_data.sql`
# tabelas sao atualizadas com `update_or_create`
# os itens dos pedidos sao substituidos e o usuario de exemplo so é criado se faltar
# a senha temporaria so é exibida quando o usuario de exemplo é criado pela primeira vez
class Command(BaseCommand):

    @transaction.atomic
    def handle(self, *args, **options):
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
            ("Carlos Menezes", date(2026, 10, 10), time(15, 0), "90.00", "45.00", Pedido.Status.PAGAMENTO_PARCIAL, [("Mini vulcão", 3, "ninho", None, None), ("Pote", 2, "bannoffe", None, None)]),
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
