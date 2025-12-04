# 📋 Sincronização de Pedidos com API Farmácia

## ✅ O que foi implementado

### 1. **Modelo Pedido Atualizado**
Novos campos adicionados para rastrear dados da API:
- `id_api` - ID único do registro na API
- `id_pedido_api` - IDPEDIDO da API
- `id_pedido_web` - IDPEDIDOWEB
- `descricao_web` - Descrição completa do produto
- `price_unit` - Preço unitário (PRUNI)
- `price_total` - Preço total (VRTOT)
- `data_atualizacao_api` - Data de atualização na API
- `tipo_identificado` - Tipo identificado automaticamente (capsula, liquido, sache, creme, etc.)

### 2. **Extração Automática de Tipo**
O sistema analisa a `DESCRICAOWEB` e identifica automaticamente:
- **Cápsula** (CAPSULA, CAP)
- **Líquido** (ML, LIQUIDO, XAROPE, TCM LIQUIDO)
- **Sachê** (SACHE, ENVELOPE)
- **Creme** (CREME)
- **Loção** (LOÇÃO)
- **Shampoo** (SHAMPOO)
- **Shot** (SHOT)
- **Óvulo** (ÓVULO)
- **Comprimido Sublingual** (SUBLINGUAL)
- **Cápsula Oleosa** (OLEOSA, OLEOSO)
- **Goma** (GOMA, GUMMY)
- **Chocolate** (CHOCOLATE)
- **Filme** (FILME)

**Pedidos com tipo "desconhecido"** aparecem marcados para ajuste manual no frontend/admin.

### 3. **Mapeamento de Etapas**
O `IDSTATUSITEMPEDIDO` é mapeado automaticamente:
- `1` → Triagem
- `2` → Produção
- `3` → Conf/Rotulagem
- `4` → Expedição

### 4. **Rastreamento de Duplicatas**
- Usa `ID` da API como chave única
- Se o registro já existe, **atualiza** em vez de duplicar
- Sem sobrescrita de dados manuais do usuário

---

## 🚀 Como Usar

### Primeira Sincronização (Histórico Completo)

Para sincronizar dados dos últimos 6 meses (~330 páginas):

```powershell
# Sincronizar 100 páginas (~5000 registros) com intervalo de 2 segundos
python manage.py sincronizar_historico_pedidos --total-paginas=100 --intervalo=2
```

**Opções disponíveis:**
- `--total-paginas=N` - Total de páginas (padrão: 10)
- `--tamanho-pagina=N` - Registros por página (padrão: 50)
- `--intervalo=N` - Segundos entre requisições (padrão: 1)

### Sincronização Manual (Uma Página)

```powershell
# Sincronizar apenas a página 1
python manage.py sincronizar_api_pedidos --pagina=1 --tamanho=50

# Sincronizar página 5
python manage.py sincronizar_api_pedidos --pagina=5
```

### Listar Pedidos Pendentes de Ajuste

```powershell
# Ver os 20 primeiros pedidos com tipo desconhecido
python manage.py listar_pedidos_desconhecidos --limite=20

# Ver os 100 primeiros
python manage.py listar_pedidos_desconhecidos --limite=100
```

---

## ⏰ Sincronização Automática (A Cada 5 Minutos)

O Celery Beat está configurado para executar automaticamente a cada 5 minutos.

### Iniciar os serviços:

**Terminal 1 - Celery Worker:**
```powershell
cd E:\Freela\farmacianovo
.\.venv\Scripts\Activate.ps1
celery -A producao_gamificada worker -l info -c 4
```

**Terminal 2 - Celery Beat:**
```powershell
cd E:\Freela\farmacianovo
.\.venv\Scripts\Activate.ps1
celery -A producao_gamificada beat -l info
```

**Terminal 3 - Django Development (opcional):**
```powershell
cd E:\Freela\farmacianovo
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

---

## 📊 Estrutura de Dados

### Exemplo de Pedido Sincronizado:

```python
{
    "id_api": 86748,  # ID único na API
    "codigo_pedido": "API-60159-86748",  # Código gerado
    "nome": "FORMULA MANIPULADA - OUTRAS: 90ML | VITAMINA D3...",
    "descricao_web": "FORMULA MANIPULADA - OUTRAS: 90ML | VITAMINA D3 GOTAS 1200 ui; VITAMINA A OLEOSA 6500 ui; VITAMINA K2MK7 OLEOSA 20 mcg; ALFATOCOFEROL OLEOSO 50 mg; TCM LIQUIDO 1 ml",
    "quantidade": 1,
    "tipo_identificado": "capsula_oleosa",  # Identificado automaticamente
    "tipo": <TipoProduto: Cápsula Oleosa>,  # Tipo do sistema
    "id_pedido_api": 45070,  # IDPEDIDO
    "id_pedido_web": 188440403,  # IDPEDIDOWEB
    "price_unit": "161.00",  # PRUNI
    "price_total": "161.00",  # VRTOT
    "data_atualizacao_api": "2025-08-06",  # DTALT
    "etapa_atual": <Etapa: 1. Triagem>,  # Mapeado de IDSTATUSITEMPEDIDO
    "status": "em_fluxo",
    "criado_em": "2025-08-06 10:30:45",  # Data/Hora da API
}
```

---

## 🔧 Ajustes Manuais

### Se o tipo foi identificado errado:

1. Abra o admin em `/admin/core/pedido/`
2. Localize o pedido
3. Altere o campo "Tipo" para o correto
4. O campo `tipo_identificado` mostra qual foi a identificação automática

### Se a etapa está errada:

1. Verifique o valor de `IDSTATUSITEMPEDIDO` na API
2. Confirme se existe uma Etapa com o grupo correto (`triagem`, `producao`, `conf_rotulagem`, `expedicao`)
3. Altere manualmente se necessário

---

## 📝 Logs e Monitoramento

### Ver logs da sincronização:

```powershell
# Sincronizar com verbosidade alta
python manage.py sincronizar_api_pedidos --pagina=1
```

### Exemplo de saída:
```
🔄 Sincronizando pedidos da página 1...
✅ Sincronização concluída!
   📝 Criados: 45
   🔄 Atualizados: 5
   📊 Total de pedidos no banco: 5237
```

---

## ⚙️ Configurações Celery

Arquivo: `producao_gamificada/celery.py`

```python
app.conf.beat_schedule = {
    'sincronizar-pedidos-a-cada-5-minutos': {
        'task': 'core.tasks.sincronizar_pedidos_da_api',
        'schedule': 300.0,  # 300 segundos = 5 minutos
        'options': {'queue': 'default'}
    },
}
```

Para mudar o intervalo, edite `300.0` para:
- `60.0` = 1 minuto
- `180.0` = 3 minutos
- `600.0` = 10 minutos

---

## 🐛 Troubleshooting

### Erro: "Nenhuma etapa ativa encontrada"
- Verifique se existe pelo menos uma Etapa com `ativa=True` em `/admin/core/etapa/`

### Erro: "Couldn't import Django"
- Ative o ambiente virtual: `.\.venv\Scripts\Activate.ps1`

### Pedidos não estão sendo sincronizados
1. Verifique se Redis está rodando: `redis-cli ping`
2. Verifique se Celery Worker está rodando
3. Verifique se Celery Beat está rodando
4. Teste manualmente: `python manage.py sincronizar_api_pedidos --pagina=1`

### API retorna erro 404
- Verifique a URL: `https://b61b2bc163ff.ngrok-free.app/tabelas/FC0M100`
- O ngrok pode ter expirado, peça uma nova URL

---

## 📱 Próximos Passos

1. ✅ Sincronização histórica completa (últimos 6 meses)
2. ✅ Sincronização automática a cada 5 minutos
3. ⏳ Criar view no admin para filtrar pedidos por `tipo_identificado`
4. ⏳ Criar dashboard com estatísticas de tipos identificados vs desconhecidos
5. ⏳ Implementar bulk edit para atualizar tipos manualmente
