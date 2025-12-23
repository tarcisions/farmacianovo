from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_pedido_options_pedido_hora_atualizacao_api'),
    ]

    operations = [
        # Primeiro, alterar o campo para permitir NULL
        migrations.AlterField(
            model_name='etapa',
            name='grupo',
            field=models.CharField(max_length=50, choices=[('triagem', 'Triagem'), ('producao', 'Produção'), ('conf_rotulagem', 'Conf/Rotulagem'), ('expedicao', 'Expedição')], null=True, blank=True),
        ),
        # Depois, remover o campo
        migrations.RemoveField(
            model_name='etapa',
            name='grupo',
        ),
    ]
