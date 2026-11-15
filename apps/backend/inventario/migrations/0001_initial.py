# gerada pelo Django 5.2.18 em 2026-11-07 23:02

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    # registra o model no estado sem criar tabela fisica, pois managed=False
    operations = [
        migrations.CreateModel(
            name='Ingrediente',
            fields=[
                ('id_ingrediente', models.AutoField(primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=100)),
                ('quantidade_disponivel', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('custo_unitario', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('data_validade', models.DateField(blank=True, null=True)),
                ('quantidade_minima', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ],
            options={
                'db_table': 'ingrediente',
                'managed': False,
            },
        ),
    ]
