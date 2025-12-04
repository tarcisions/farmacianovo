## 🎯 RESUMO: Sincronização Automática da API

Você agora tem um sistema **SIMPLES** e **AUTOMÁTICO** para chamar sua API a cada 5 minutos. Sem Celery, sem Redis complicado.

---

## ⚡ Quick Start

### 1️⃣ Configurar a URL
Abra `core/scheduler.py` e edite:

```python
CONFIG = {
    'url_base': 'https://b61b2bc163ff.ngrok-free.app/tabelas/FC0M100',
    'intervalo_minutos': 5,  # Mude para quantos minutos quiser
    'paginacoes': [
        {'pagina': 1, 'tamanho': 50},
        # Adicione mais linhas se quiser múltiplas páginas
    ],
    'ativo': True,  # Mude para False se quiser desativar
}
```

### 2️⃣ Rodar o servidor
```bash
python manage.py runserver
```

**Pronto!** O scheduler inicia automaticamente.

### 3️⃣ Verificar status (opcional)
```bash
python manage.py scheduler status
```

---

## 📡 Exemplos de Uso

### Exemplo 1: Uma única página
```python
'paginacoes': [
    {'pagina': 1, 'tamanho': 50},
]
# Chama: ?pagina=1&tamanho=50
```

### Exemplo 2: Múltiplas páginas
```python
'paginacoes': [
    {'pagina': 1, 'tamanho': 50},
    {'pagina': 2, 'tamanho': 50},
    {'pagina': 3, 'tamanho': 50},
]
# Chama as 3 URLs a cada 5 minutos
```

### Exemplo 3: Intervalo customizado
```python
'intervalo_minutos': 10,  # A cada 10 minutos
```

---

## 🎮 Comandos (Linha de Comando)

```bash
# Ver status
python manage.py scheduler status

# Iniciar
python manage.py scheduler start

# Parar
python manage.py scheduler stop

# Sincronizar agora (manual)
python manage.py scheduler agora
```

---

## 🌐 Interface Web (Opcional)

Se quiser uma interface visual para controlar o scheduler:

1. Adicione isto a `core/urls.py` (já feito):
   ```python
   path('api/scheduler/status/', views_scheduler.status_scheduler, name='scheduler_status'),
   path('api/scheduler/iniciar/', views_scheduler.iniciar_scheduler, name='scheduler_iniciar'),
   path('api/scheduler/parar/', views_scheduler.parar_scheduler, name='scheduler_parar'),
   path('api/scheduler/sincronizar/', views_scheduler.sincronizar_agora, name='scheduler_sincronizar'),
   ```

2. Crie uma view para servir a template:
   ```python
   # Em core/views.py
   def scheduler_view(request):
       return render(request, 'core/scheduler.html')
   ```

3. Adicione a URL:
   ```python
   path('scheduler/', views.scheduler_view, name='scheduler_view'),
   ```

---

## 📊 Logs

Os logs aparecem no console do runserver:

```
✓ Scheduler iniciado! Sincronização a cada 5 minuto(s)
============================================================
SINCRONIZAÇÃO INICIADA - 2025-12-03 10:30:45
============================================================
✓ API chamada com sucesso - Página 1, Tamanho 50
SINCRONIZAÇÃO FINALIZADA - 1 chamada(s)
============================================================
```

---

## ⚙️ Arquivos Criados

- `core/scheduler.py` - Lógica principal
- `core/management/commands/scheduler.py` - Comando Django
- `core/views_scheduler.py` - Views para API (opcional)
- `templates/core/scheduler.html` - Interface web (opcional)
- `SINCRONIZACAO_AUTOMATICA.md` - Documentação completa

---

## 🚨 Troubleshooting

**Problema: Scheduler não inicia**
- Verifique se `'ativo': True` em `core/scheduler.py`
- Veja os logs no console do runserver

**Problema: API não é chamada**
- Teste manualmente: `python manage.py scheduler agora`
- Verifique a URL em `CONFIG['url_base']`

**Problema: Chama múltiplas vezes**
- Verifique `paginacoes` em `CONFIG`
- Cada entrada = uma chamada

---

## 🎁 Bônus: Desativar para Desenvolvimento

Se não quer que a API seja chamada enquanto está desenvolvendo:

```python
'ativo': False,  # Muda para False
```

E quando quiser ativar de novo:
```python
'ativo': True,
```

---

## 📦 Dependências

Já instalado (adicionado ao requirements.txt):
- `APScheduler==3.10.4`

---

## 🔄 Fluxo de Execução

```
runserver iniciado
        ↓
Django carrega apps
        ↓
CoreConfig.ready() executado
        ↓
AgendadorSincronizacao.iniciar()
        ↓
APScheduler inicia em background
        ↓
A cada 5 min (ou seu intervalo): SincronizadorAPI.sincronizar()
        ↓
Chamada HTTP para cada paginação em CONFIG
        ↓
Logs no console + arquivo (se configurado)
```

---

## ✅ Pronto para Usar!

Sua sincronização automática está 100% funcional. Edite `core/scheduler.py` conforme necessário e está feito!

Qualquer dúvida, consulte `SINCRONIZACAO_AUTOMATICA.md`.
