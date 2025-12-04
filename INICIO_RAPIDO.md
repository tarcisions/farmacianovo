# ⚡ GUIA RÁPIDO - Sincronização de Pedidos

## 🎯 1. TESTE RÁPIDO (2 minutos)

```powershell
# Ativar ambiente
.\.venv\Scripts\Activate.ps1

# Rodar teste com dados simulados
python manage.py testar_sincronizacao
```

**Esperado:**
```
✅ Teste concluído!
   📝 Criados: 3
   🔄 Atualizados: 0
   📊 Total no banco: 5
```

---

## 🚀 2. SINCRONIZAR DADOS REAIS

### Opção A: Uma página (50 registros)
```powershell
python manage.py sincronizar_api_pedidos --pagina=1 --tamanho=50
```

### Opção B: Histórico completo (100 páginas = 5000 registros)
```powershell
python manage.py sincronizar_historico_pedidos --total-paginas=100 --intervalo=2
```

---

## ⏰ 3. ATIVAR SINCRONIZAÇÃO AUTOMÁTICA (A CADA 5 MIN)

### Terminal 1 - Worker Celery
```powershell
.\.venv\Scripts\Activate.ps1
celery -A producao_gamificada worker -l info -c 4
```

### Terminal 2 - Beat Celery (novo terminal)
```powershell
.\.venv\Scripts\Activate.ps1
celery -A producao_gamificada beat -l info
```

### Terminal 3 - Django (opcional)
```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

---

## 📊 4. MONITORAR PROGRESSO

### Ver pedidos com tipo desconhecido
```powershell
python manage.py listar_pedidos_desconhecidos --limite=20
```

### Contar total de pedidos
```powershell
python manage.py shell
>>> from core.models import Pedido
>>> Pedido.objects.count()
```

---

## 🎓 ENTENDER O FUNCIONAMENTO

### Extração de Tipo
```
"FORMULA MANIPULADA - CAPSULA: 180CAP | DAPAGLIFOZINA 10 mg"
                       ↓
              Detecta: "CAPSULA"
                       ↓
              Atribui: capsula
```

### Mapeamento de Etapa
```
IDSTATUSITEMPEDIDO=1  →  Triagem
IDSTATUSITEMPEDIDO=2  →  Produção
IDSTATUSITEMPEDIDO=3  →  Conf/Rotulagem
IDSTATUSITEMPEDIDO=4  →  Expedição
```

### Rastreamento de Duplicatas
```
ID 86748  ← Chave única
  Se existe: ATUALIZA
  Se não existe: CRIA
```

---

## ✅ CHECKLIST

- [ ] Ambiente virtual ativado
- [ ] `requests` instalado (`pip install requests`)
- [ ] Migrations aplicadas (`python manage.py migrate`)
- [ ] Teste executado com sucesso
- [ ] Celery Worker rodando
- [ ] Celery Beat rodando
- [ ] Pedidos sendo sincronizados a cada 5 minutos

---

## ⚠️ TROUBLESHOOTING

**Erro: "ModuleNotFoundError: No module named 'requests'"**
```powershell
pip install requests
```

**Erro: "Nenhuma etapa ativa encontrada"**
- Vá para: `/admin/core/etapa/`
- Verifique se existe etapa com `ativa=True`
- Crie se necessário

**API retorna erro 500**
- URL ngrok pode ter expirado
- Peça uma nova URL ao proprietário da API

**Celery não está sincronizando**
1. Verifique se Redis está rodando: `redis-cli ping`
2. Verifique se Worker está rodando
3. Verifique se Beat está rodando
4. Teste manual: `python manage.py sincronizar_api_pedidos --pagina=1`

---

## 📚 DOCUMENTAÇÃO COMPLETA

- `API_SINCRONIZACAO.md` - Guia completo
- `RESUMO_IMPLEMENTACAO.md` - Visão geral técnica

---

## 💡 DICAS

1. **Sincronização Lenta?**
   - Reduza `--intervalo` para 0.5 segundos
   - Ou execute múltiplas instâncias do Worker

2. **Mudar intervalo de sincronização?**
   - Edite `producao_gamificada/celery.py`
   - Procure por `'schedule': 300.0`
   - Mude para: 60 (1 min), 180 (3 min), 600 (10 min)

3. **Ver logs detalhados?**
   - Execute com verbosidade: `python manage.py sincronizar_api_pedidos --pagina=1 -v 2`

---

## 🎯 Próxima Execução

```powershell
# No seu próximo commit:
git add requirements.txt
git add core/models.py
git add core/tasks.py
git add producao_gamificada/celery.py
git add core/management/commands/
git add *.md
git commit -m "feat: sincronização automática com API de pedidos"
```

---

Você está pronto! 🚀
