from django.db import migrations


# Reposição interna não tem pagamento, mas o modal gravava o sinal digitado e a
# 0004 marcou esses sinais como pagos. Zera os dois para a validação nova aceitar
# edições desses pedidos e eles saírem dos pagamentos.
def zerar_sinal_da_reposicao_interna(apps, schema_editor):
    Pedido = apps.get_model("pedido", "Pedido")
    Pedido.objects.filter(tipo="interno").exclude(valor_sinal=0, sinal_pago=False).update(
        valor_sinal=0, sinal_pago=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("pedido", "0004_pedido_sinal_pago"),
    ]

    operations = [
        migrations.RunPython(zerar_sinal_da_reposicao_interna, migrations.RunPython.noop),
    ]
