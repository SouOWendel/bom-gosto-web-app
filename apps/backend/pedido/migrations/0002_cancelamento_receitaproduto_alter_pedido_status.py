# gerada pelo Django 5.2.18 em 2026-11-07 23:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedido', '0001_initial'),
    ]

    # registra models nao gerenciados sem criar tabelas e choices sem alterar o schema sql
    operations = [
        migrations.CreateModel(
            name='Cancelamento',
            fields=[
                ('id_cancelamento', models.AutoField(primary_key=True, serialize=False)),
                ('destino', models.CharField(blank=True, max_length=20, null=True)),
                ('data_cancelamento', models.DateField(blank=True, null=True)),
                ('pedido', models.ForeignKey(db_column='pedido_id', on_delete=django.db.models.deletion.PROTECT, to='pedido.pedido')),
            ],
            options={
                'db_table': 'cancelamento',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ReceitaProduto',
            fields=[
                ('id_receita_produto', models.AutoField(primary_key=True, serialize=False)),
                ('quantidade', models.DecimalField(decimal_places=3, max_digits=10)),
                ('unidade_medida', models.CharField(blank=True, max_length=20, null=True)),
                ('custo_unitario', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('produto', models.ForeignKey(db_column='id_produto', on_delete=django.db.models.deletion.CASCADE, to='pedido.produto')),
                ('receita', models.ForeignKey(db_column='id_receita', on_delete=django.db.models.deletion.CASCADE, to='pedido.receita')),
            ],
            options={
                'db_table': 'receita_produto',
                'managed': False,
            },
        ),
        migrations.AlterField(
            model_name='pedido',
            name='status',
            field=models.CharField(choices=[('pedido_feito', 'Pedido feito'), ('em_producao', 'Em produção'), ('producao_concluida', 'Produção concluída'), ('concluido', 'Concluído'), ('cancelado', 'Cancelado')], default='pedido_feito', max_length=20),
        ),
    ]
