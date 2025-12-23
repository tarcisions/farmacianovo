from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_etapa_pontos_fixos_etapa'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='checklist',
            name='tipo_contagem_sedex',
        ),
    ]
