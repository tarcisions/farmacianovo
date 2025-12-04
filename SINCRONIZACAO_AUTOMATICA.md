# Sincronização Automática da API

Sistema simples de sincronização automática usando **APScheduler** (sem Celery/Redis complexo).

## 🚀 Como Funciona

O sistema chama sua API automaticamente a cada **5 minutos** (configurável) com os parâmetros que você definir.

**Características:**
- ✅ Funciona com `python manage.py runserver`
- ✅ Sem dependências externas (Redis, Celery, etc)
- ✅ Fácil de configurar
- ✅ Pode sincronizar múltiplas páginas
- ✅ Logs detalhados

## ⚙️ Configuração

Edite o arquivo `core/scheduler.py`, seção `CONFIG`:

```python
CONFIG = {
    'url_base': 'https://b61b2bc163ff.ngrok-free.app/tabelas/FC0M100',
    'intervalo_minutos': 5,  # Intervalo entre chamadas
    'paginacoes': [
        {'pagina': 1, 'tamanho': 50},
        # Adicione mais se precisar:
        # {'pagina': 2, 'tamanho': 50},
        # {'pagina': 3, 'tamanho': 100},
    ],
    'timeout': 30,  # Segundos para timeout
    'ativo': True,  # Ativa/desativa o scheduler
}
```

## 📝 Comandos

### Iniciar o scheduler
```bash
python manage.py scheduler start
```

### Ver status
```bash
python manage.py scheduler status
```

### Parar o scheduler
```bash
python manage.py scheduler stop
```

### Sincronizar agora (manual)
```bash
python manage.py scheduler agora
```

## 🔧 Uso com runserver

Quando você executa:
```bash
python manage.py runserver
```

O scheduler **inicia automaticamente** (se `ativo=True` na config).

Os logs aparecem no terminal/console:

```
✓ Scheduler iniciado! Sincronização a cada 5 minuto(s)
============================================================
SINCRONIZAÇÃO INICIADA - 2025-12-03 10:30:45
============================================================
✓ API chamada com sucesso - Página 1, Tamanho 50
SINCRONIZAÇÃO FINALIZADA - 1 chamada(s)
============================================================
```

## 📊 Exemplo: Múltiplas Páginas

Se você quiser sincronizar várias páginas de uma vez:

```python
'paginacoes': [
    {'pagina': 1, 'tamanho': 50},
    {'pagina': 2, 'tamanho': 50},
    {'pagina': 3, 'tamanho': 50},
]
```

Ele vai chamar:
- `https://...?pagina=1&tamanho=50`
- `https://...?pagina=2&tamanho=50`
- `https://...?pagina=3&tamanho=50`

Tudo a cada 5 minutos.

## 🛑 Desativar Temporariamente

Se não quiser que o scheduler rode, altere em `core/scheduler.py`:

```python
'ativo': False,  # Muda para False
```

## 📡 Monitorar Logs

Para ver os logs em tempo real:

```bash
# Terminal 1: rodando o servidor
python manage.py runserver

# Terminal 2: monitorando logs (adicione isto ao seu settings)
```

Adicione isto ao seu `producao_gamificada/settings.py` para ter logs mais detalhados:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'sincronizacao.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'core.scheduler': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

## 🔄 Fluxo

```
runserver iniciado
    ↓
CoreConfig.ready() executado
    ↓
AgendadorSincronizacao.iniciar()
    ↓
APScheduler inicia em background
    ↓
A cada 5 min: SincronizadorAPI.sincronizar()
    ↓
Chamada HTTP para cada paginação configurada
    ↓
Logs salvos em arquivo e/ou console
```

## 📦 Instalação

Já adicionado ao `requirements.txt`:
```
APScheduler==3.10.4
```

Se não tiver instalado:
```bash
pip install APScheduler==3.10.4
```

## ⚠️ Observações

1. **runserver**: O scheduler roda em uma thread separada, não bloqueia o servidor
2. **Múltiplas instâncias**: Se rodar `runserver` mais de uma vez, pode ter múltiplos schedulers. Use `max_instances=1` para evitar
3. **Produção**: Para produção, considere usar Celery ou similar
4. **Ngrok**: Se o ngrok expirar, você precisará atualizar a URL em `CONFIG`

## 🆘 Troubleshooting

**Scheduler não inicia:**
- Verifique se `'ativo': True` em `core/scheduler.py`
- Veja os logs no console

**API não é chamada:**
- Verifique a URL em `CONFIG['url_base']`
- Teste manualmente: `python manage.py scheduler agora`
- Verifique os logs para erros de conexão

**Muitas chamadas:**
- Verifique `'paginacoes'` em `CONFIG` - cada entrada = uma chamada
- Aumente `'intervalo_minutos'` se necessário
