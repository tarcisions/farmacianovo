from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_remove_checklist_tipo_contagem_sedex'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='status_fila',
            field=models.CharField(
                choices=[('ativo', 'Ativo'), ('pendente', 'Pendente')],
                default='ativo',
                help_text='Status na fila de trabalho (Ativo/Pendente)',
                max_length=20
            ),
        ),
    ]
