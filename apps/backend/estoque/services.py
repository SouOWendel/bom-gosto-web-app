from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Estoque


# Consome primeiro os lotes com validade mais próxima e protege os saldos contra concorrência.
@transaction.atomic
def baixar_lotes(produto_id, quantidade):
    """Consome lotes válidos por validade, sem permitir saldo negativo."""
    restante = Decimal(quantidade)
    hoje = timezone.localdate()
    lotes = Estoque.objects.select_for_update().filter(produto_id=produto_id).filter(
        Q(data_validade__isnull=True) | Q(data_validade__gte=hoje)
    ).order_by("data_validade", "id_estoque")
    for lote in lotes:
        consumo = min(lote.quantidade_disponivel, restante)
        if consumo:
            saldo_anterior = lote.quantidade_disponivel
            lote.quantidade_disponivel -= consumo
            # O custo do lote acompanha a quantidade que sobrou (rateio proporcional).
            if lote.custo is not None:
                lote.custo = (lote.custo * lote.quantidade_disponivel / saldo_anterior).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            lote.save(update_fields=["quantidade_disponivel", "custo"])
            restante -= consumo
        if restante <= 0:
            return
    raise ValidationError({"estoque": "Não há saldo válido suficiente para concluir o pedido."})
