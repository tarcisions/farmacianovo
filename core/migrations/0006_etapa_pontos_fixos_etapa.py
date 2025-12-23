from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_remove_etapa_grupo'),
    ]

    operations = [
        migrations.AddField(
            model_name='etapa',
            name='pontos_fixos_etapa',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Pontos dados ao concluir a etapa (quando não há checklists)', max_digits=10),
        ),
    ]
