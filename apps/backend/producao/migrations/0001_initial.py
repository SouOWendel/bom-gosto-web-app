# gerada pelo Django 5.2.18 em 2026-11-07 23:02

import django.db.models.deletion
from django.db import migrations, models

# cria a tabela ingrediente_receita no banco de dados, que representa a relação entre ingredientes e receitas. a tabela contem informacoes sobre a quantidade necessaria de cada ingrediente para uma receita específica
class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('inventario', '0001_initial'),
        ('pedido', '0002_cancelamento_receitaproduto_alter_pedido_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='IngredienteReceita',
            fields=[
                ('id_ingrediente_receita', models.AutoField(primary_key=True, serialize=False)),
                ('quantidade_necessaria', models.DecimalField(decimal_places=2, max_digits=10)),
                ('ingrediente', models.ForeignKey(db_column='ingrediente_id', on_delete=django.db.models.deletion.PROTECT, to='inventario.ingrediente')),
                ('receita', models.ForeignKey(db_column='receita_id', on_delete=django.db.models.deletion.CASCADE, related_name='composicao', to='pedido.receita')),
            ],
            options={
                'db_table': 'ingrediente_receita',
                'managed': False,
            },
        ),
    ]
