from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from estoque.models import Estoque
from inventario.models import Ingrediente
from pedido.models import Cancelamento, ItemPedido, Pedido, Produto, Receita, ReceitaProduto, status_operacional
from .models import IngredienteReceita

CENTAVO = Decimal("0.01")


# Obtém a quantidade usada para comparar o item com o Estoque e a receita.
def _quantidade_item(item):
    return Decimal(item.quantidade or item.quantidade_peso or 0)


# Escolhe a receita indicada no item ou a receita principal do produto.
def _receita_item(item):
    return item.receita or (item.produto.receita if item.produto_id else None)


# Calcula os ingredientes exigidos para a parte do pedido que precisa ser produzida.
def _ingredientes_previstos(pedido):
    previstos = {}
    ausencias = []
    sugestoes = []
    for item in pedido.itens.select_related("produto__receita", "receita"):
        quantidade = _quantidade_item(item)
        # Reposição interna produz toda a quantidade solicitada; não consome
        # o saldo de vitrine que já existe para clientes.
        if item.produto_id and pedido.tipo == Pedido.Tipo.EXTERNO:
            saldo_pronto = Estoque.objects.verificar_disponibilidade(item.produto_id, quantidade)["quantidade_disponivel"]
            quantidade = max(Decimal("0"), quantidade - saldo_pronto)
            if quantidade == 0:
                continue
        receita = _receita_item(item)
        if receita is None and item.produto_id:
            receita_ids = ReceitaProduto.objects.filter(produto_id=item.produto_id).values_list("receita_id", flat=True)
            receitas = list(Receita.objects.filter(pk__in=receita_ids).order_by("nome"))
            sugestoes.extend({"id_receita": r.pk, "nome": r.nome} for r in receitas)
            if not receitas:
                ausencias.append({"item_pedido": item.pk, "tipo": "receita", "motivo": "Nenhuma receita associada ao produto."})
            continue
        if receita is None:
            ausencias.append({"item_pedido": item.pk, "tipo": "receita", "motivo": "O item não possui receita aplicável."})
            continue
        if not receita.rendimento_quantidade or receita.rendimento_quantidade <= 0:
            ausencias.append({"item_pedido": item.pk, "tipo": "rendimento", "motivo": "A receita não tem rendimento válido."})
            continue
        composicao = list(IngredienteReceita.objects.filter(receita_id=receita.pk).select_related("ingrediente").order_by("ingrediente_id"))
        if not composicao:
            ausencias.append({"item_pedido": item.pk, "tipo": "ingredientes", "motivo": f"A receita {receita.nome} ainda não tem ingredientes."})
            continue
        fator = quantidade / receita.rendimento_quantidade
        for componente in composicao:
            necessario = (componente.quantidade_necessaria * fator).quantize(CENTAVO, rounding=ROUND_HALF_UP)
            linha = previstos.setdefault(componente.ingrediente_id, {"ingrediente": componente.ingrediente, "necessario": Decimal("0")})
            linha["necessario"] += necessario
    return previstos, ausencias, sugestoes


# Consolida estoque pronto, receitas aplicáveis e insuficiência de ingredientes.
def analisar_pedido(pedido):
    """Combina saldo de produto pronto, receitas e disponibilidade de ingredientes."""
    previstos, ausencias, sugestoes = _ingredientes_previstos(pedido)
    itens = []
    for item in pedido.itens.select_related("produto", "receita"):
        quantidade = _quantidade_item(item)
        if item.produto_id:
            saldo = Estoque.objects.verificar_disponibilidade(item.produto_id, quantidade)
        else:
            saldo = {"quantidade_solicitada": quantidade, "quantidade_disponivel": Decimal("0"), "disponivel": False, "encaminhar_para_producao": True}
        itens.append({"id_item_pedido": item.pk, "produto_id": item.produto_id, "receita_id": (_receita_item(item).pk if _receita_item(item) else None), **saldo})
    ingredientes = []
    for linha in previstos.values():
        ingrediente = linha["ingrediente"]
        disponivel = ingrediente.quantidade_disponivel or Decimal("0")
        validade = ingrediente.data_validade
        alerta_validade = None
        if validade:
            dias = (validade - timezone.localdate()).days
            if dias <= 0:
                nivel = "critico"
            elif dias <= 7:
                nivel = "atencao"
            elif dias <= 15:
                nivel = "preventivo"
            else:
                nivel = None
            if nivel:
                alerta_validade = {"nivel": nivel, "dias_para_vencer": dias}
        minimo = ingrediente.quantidade_minima
        ingredientes.append({"id_ingrediente": ingrediente.pk, "nome": ingrediente.nome, "necessario": linha["necessario"], "disponivel": disponivel, "suficiente": disponivel >= linha["necessario"], "abaixo_do_minimo": (minimo is not None and disponivel < minimo), "data_validade": validade, "alerta_validade": alerta_validade})
    return {"estoque": itens, "receitas_sugeridas": sugestoes, "ausencias": ausencias, "ingredientes_insuficientes": [i for i in ingredientes if not i["suficiente"]], "ingredientes": ingredientes, "encaminhar_para_producao": any(not i["disponivel"] for i in itens)}


# Soma consumos repetidos e valida todos os saldos antes de qualquer baixa.
def _consumos_confirmados(consumos, lock=False):
    # Agrupa linhas repetidas para validar e baixar cada ingrediente sem ultrapassar o saldo.
    totais = {}
    for linha in consumos:
        ingrediente_id = linha["ingrediente_id"]
        totais[ingrediente_id] = totais.get(ingrediente_id, Decimal("0")) + linha["quantidade"]
    ids = list(totais)
    qs = Ingrediente.objects.filter(pk__in=ids).order_by("pk")
    if lock:
        qs = qs.select_for_update()
    ingredientes = {i.pk: i for i in qs}
    resultado = []
    for ingrediente_id, quantidade in totais.items():
        ingrediente = ingredientes.get(ingrediente_id)
        if ingrediente is None:
            raise ValidationError({"consumos": f"Ingrediente {ingrediente_id} não encontrado."})
        if quantidade < 0:
            raise ValidationError({"consumos": "As quantidades não podem ser negativas."})
        saldo = ingrediente.quantidade_disponivel or Decimal("0")
        if saldo < quantidade:
            raise ValidationError({"consumos": f"Saldo insuficiente para {ingrediente.nome}."})
        resultado.append((ingrediente, quantidade))
    return resultado


# Baixa ingredientes, calcula custo e gera os lotes uma única vez para o pedido.
@transaction.atomic
def concluir_producao(pedido, consumos, data_validade):
    # O status do pedido funciona como trava idempotente junto com as baixas e entradas atômicas.
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    pedido.status = status_operacional(pedido.status)
    if pedido.status == Pedido.Status.PRODUCAO_CONCLUIDA:
        raise ValidationError({"status": "A produção deste pedido já foi concluída."})
    if pedido.status != Pedido.Status.EM_PRODUCAO:
        raise ValidationError({"status": "Inicie a produção antes de concluí-la."})
    if not consumos:
        raise ValidationError({"consumos": "Informe os ingredientes realmente utilizados (inclua quantidade zero quando aplicável)."})
    previstos, ausencias, _ = _ingredientes_previstos(pedido)
    if ausencias:
        raise ValidationError({"receitas": ausencias})
    informados = {linha["ingrediente_id"] for linha in consumos}
    faltantes = set(previstos) - informados
    if faltantes:
        raise ValidationError({"consumos": f"Informe também os ingredientes {', '.join(map(str, sorted(faltantes)))}; use zero quando não foram utilizados."})
    consumos_ok = _consumos_confirmados(consumos, lock=True)
    custo = Decimal("0")
    for ingrediente, quantidade in consumos_ok:
        custo += quantidade * (ingrediente.custo_unitario or Decimal("0"))
    for ingrediente, quantidade in consumos_ok:
        ingrediente.quantidade_disponivel = (ingrediente.quantidade_disponivel or Decimal("0")) - quantidade
        ingrediente.save(update_fields=["quantidade_disponivel"])

    saidas = []
    for item in pedido.itens.select_related("produto__receita", "receita"):
        produto = item.produto
        receita = _receita_item(item)
        if produto is None and receita:
            produto = receita.produtos.order_by("id_produto").first()
            if produto is None:
                relacao = ReceitaProduto.objects.filter(receita_id=receita.pk).select_related("produto").first()
                produto = relacao.produto if relacao else None
        if produto is None:
            raise ValidationError({"itens": "Associe um produto à receita antes de concluir a produção."})
        solicitado = _quantidade_item(item)
        # Pedidos internos repõem o estoque integralmente; externos aproveitam
        # o produto pronto disponível e produzem somente a diferença.
        saldo = (
            Estoque.objects.verificar_disponibilidade(produto.pk, solicitado)["quantidade_disponivel"]
            if pedido.tipo == Pedido.Tipo.EXTERNO
            else Decimal("0")
        )
        quantidade_produzida = max(Decimal("0"), solicitado - saldo)
        if quantidade_produzida > 0:
            saidas.append((produto, quantidade_produzida))
    total_produzido = sum((quantidade for _, quantidade in saidas), Decimal("0"))
    for produto, quantidade in saidas:
        custo_lote = (custo * quantidade / total_produzido).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        Estoque.objects.create(produto=produto, quantidade_disponivel=quantidade, data_validade=data_validade, custo=custo_lote)
    pedido.status = Pedido.Status.PRODUCAO_CONCLUIDA
    pedido.save(update_fields=["status"])
    return {"pedido": pedido, "custo": custo}


# Registra o cancelamento e aplica o destino escolhido junto às baixas necessárias.
@transaction.atomic
def cancelar_pedido(pedido, consumos, destino, produto_aproveitado=None):
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    pedido.status = status_operacional(pedido.status)
    if pedido.status in (Pedido.Status.CONCLUIDO, Pedido.Status.CANCELADO):
        raise ValidationError({"status": "Somente pedidos ainda não concluídos podem ser cancelados."})
    producao_finalizada = pedido.status == Pedido.Status.PRODUCAO_CONCLUIDA
    if producao_finalizada and destino == "descarte":
        raise ValidationError({"destino": "O schema atual não relaciona o lote produzido ao pedido; não é seguro descartá-lo automaticamente."})
    if Cancelamento.objects.filter(pedido=pedido).exists():
        raise ValidationError({"pedido": "Este pedido já possui um cancelamento registrado."})
    # A produção concluída já baixou os ingredientes; o cancelamento não repete essa baixa.
    consumos_ok = [] if pedido.status == Pedido.Status.PRODUCAO_CONCLUIDA else _consumos_confirmados(consumos, lock=True)
    custo = Decimal("0")
    for ingrediente, quantidade in consumos_ok:
        custo += quantidade * (ingrediente.custo_unitario or Decimal("0"))
    for ingrediente, quantidade in consumos_ok:
        ingrediente.quantidade_disponivel = (ingrediente.quantidade_disponivel or Decimal("0")) - quantidade
        ingrediente.save(update_fields=["quantidade_disponivel"])
    # Se a produção já gerou o lote, ele permanece disponível e não recebe uma segunda entrada.
    if destino == "estoque" and not producao_finalizada:
        if not produto_aproveitado:
            raise ValidationError({"produto_aproveitado": "Informe os dados do produto reaproveitado."})
        produto = Produto.objects.create(nome=produto_aproveitado["nome"], preco_venda=produto_aproveitado["preco_venda"])
        Estoque.objects.create(produto=produto, quantidade_disponivel=produto_aproveitado["quantidade"], data_validade=produto_aproveitado["data_validade"], custo=produto_aproveitado["custo"])
    cancelamento = Cancelamento.objects.create(pedido=pedido, destino=destino, data_cancelamento=timezone.localdate())
    pedido.status = Pedido.Status.CANCELADO
    pedido.save(update_fields=["status"])
    return pedido, cancelamento
