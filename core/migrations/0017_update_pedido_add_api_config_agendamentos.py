# Generated migration - Update Pedido model and add new API configuration models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_remove_controlepergunta_pontuacao_pergunta'),
    ]

    operations = [
        # Create ConfiguracaoAPI model
        migrations.CreateModel(
            name='ConfiguracaoAPI',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Nome descritivo da API (ex: API Pedidos, API Estoque)', max_length=200, unique=True)),
                ('url_base', models.URLField(help_text='URL base da API (ex: https://api.exemplo.com/tabelas/FC0M100)')),
                ('descricao', models.TextField(blank=True, help_text='Descrição sobre a API e seu propósito')),
                ('tipo_autenticacao', models.CharField(choices=[('nenhuma', 'Nenhuma'), ('bearer_token', 'Bearer Token'), ('api_key', 'API Key'), ('login_senha', 'Usuário e Senha'), ('custom', 'Customizada')], default='nenhuma', help_text='Tipo de autenticação requerida pela API', max_length=20)),
                ('bearer_token', models.CharField(blank=True, help_text='Token para autenticação Bearer (se aplicável)', max_length=500)),
                ('api_key', models.CharField(blank=True, help_text='API Key para autenticação (se aplicável)', max_length=500)),
                ('usuario', models.CharField(blank=True, help_text='Usuário para autenticação (se aplicável)', max_length=200)),
                ('senha', models.CharField(blank=True, help_text='Senha para autenticação (se aplicável)', max_length=200)),
                ('headers_customizados', models.JSONField(blank=True, help_text='Headers customizados em formato JSON (ex: {"Custom-Header": "value"})', null=True)),
                ('timeout', models.IntegerField(default=30, help_text='Timeout em segundos para requisições')),
                ('ativa', models.BooleanField(default=True, help_text='Se a API está ativa para sincronização')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuração de API',
                'verbose_name_plural': 'Configurações de API',
            },
        ),
        # Create AgendamentoSincronizacao model
        migrations.CreateModel(
            name='AgendamentoSincronizacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Nome descritivo do agendamento (ex: Sincronização Matinal)', max_length=200)),
                ('executar_todos_os_dias', models.BooleanField(default=True, help_text='Se deve executar todos os dias')),
                ('dias_semana', models.JSONField(blank=True, default=list, help_text="Lista de dias se não for todos os dias (ex: ['segunda', 'quarta', 'sexta'])")),
                ('horario_execucao', models.TimeField(help_text='Horário em que a sincronização será executada (ex: 06:00)')),
                ('paginacoes', models.JSONField(default=list, help_text='Lista de dicts com paginações (ex: [{"pagina": 1, "tamanho": 50}, {"pagina": 2, "tamanho": 50}])')),
                ('ativo', models.BooleanField(default=True, help_text='Se o agendamento está ativo')),
                ('descricao', models.TextField(blank=True, help_text='Notas adicionais sobre este agendamento')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('api', models.ForeignKey(help_text='API a ser sincronizada', on_delete=django.db.models.deletion.CASCADE, related_name='agendamentos', to='core.configuracaoapi')),
            ],
            options={
                'verbose_name': 'Agendamento de Sincronização',
                'verbose_name_plural': 'Agendamentos de Sincronização',
                'ordering': ['api', 'horario_execucao'],
            },
        ),
        # Modify Pedido model - Remove id_pedido_api and id_pedido_web, add serieo, modify id_api
        migrations.RemoveField(
            model_name='pedido',
            name='id_pedido_api',
        ),
        migrations.RemoveField(
            model_name='pedido',
            name='id_pedido_web',
        ),
        migrations.AddField(
            model_name='pedido',
            name='serieo',
            field=models.CharField(blank=True, default='0', help_text='Série do item (SERIEO) vindo da API', max_length=20),
        ),
        migrations.AlterField(
            model_name='pedido',
            name='id_api',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True, unique=True),
        ),
    ]
