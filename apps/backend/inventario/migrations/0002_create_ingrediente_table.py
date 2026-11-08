from django.db import migrations


def create_ingrediente(apps, schema_editor):
    model = apps.get_model("inventario", "Ingrediente")
    with schema_editor.connection.cursor() as cursor:
        tables = schema_editor.connection.introspection.table_names(cursor)
    if model._meta.db_table not in tables:
        schema_editor.create_model(model)

class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="ingrediente",
            options={"db_table": "ingrediente"},
        ),
        migrations.RunPython(create_ingrediente),
    ]
