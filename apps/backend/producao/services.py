from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework.exceptions import ValidationError

from estoque.models import Estoque
from inventario.models import Ingrediente
from .models import IngredienteReceita


CENTAVO = Decimal("0.01")


@transaction.atomic
def registrar_producao(*, produto, quantidade_produzida, data_validade, custo):
    receita = produto.receita

    if receita is None:
        raise ValidationError({
            "produto_id": "O produto precisa estar associado a uma receita."
        })

    rendimento = receita.rendimento_quantidade
    if rendimento is None or rendimento <= 0:
        raise ValidationError({
            "produto_id": "A receita precisa ter rendimento maior que zero."
        })

    composicao = list(
        IngredienteReceita.objects
        .filter(receita_id=receita.pk)
        .order_by("ingrediente_id")
    )
    if not composicao:
        raise ValidationError({
            "produto_id": "A receita não possui ingredientes cadastrados."
        })

    ids = [item.ingrediente_id for item in composicao]
    ingredientes = {
        item.pk: item
        for item in Ingrediente.objects
        .select_for_update()
        .filter(pk__in=ids)
        .order_by("pk")
    }

    fator = quantidade_produzida / rendimento
    consumos = []

    for item in composicao:
        ingrediente = ingredientes[item.ingrediente_id]
        quantidade = (
            item.quantidade_necessaria * fator
        ).quantize(CENTAVO, rounding=ROUND_HALF_UP)

        if quantidade <= 0:
            raise ValidationError({
                "quantidade_produzida": "A quantidade é pequena demais."
            })

        saldo = ingrediente.quantidade_disponivel
        if saldo is None or saldo < quantidade:
            raise ValidationError({
                "inventario": (
                    f"Saldo insuficiente ou não informado para "
                    f"{ingrediente.nome}."
                )
            })

        consumos.append((ingrediente, quantidade))

    # Só grava depois de validar todos os ingredientes.
    for ingrediente, quantidade in consumos:
        ingrediente.quantidade_disponivel -= quantidade
        ingrediente.save(update_fields=["quantidade_disponivel"])

    return Estoque.objects.create(
        produto=produto,
        quantidade_disponivel=quantidade_produzida,
        data_validade=data_validade,
        custo=custo,
    )