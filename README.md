# 📊 Sistema de Produção Gamificada

**Sistema web completo de gestão de produção para farmácias de manipulação**, com fluxo de trabalho automatizado, sincronização de API e sistema de gamificação para motivar funcionários.

**Tecnologias:** Django 4.x, PostgreSQL, WebSockets (Channels), APScheduler, Bootstrap 5

📖 **Para uma visão completa das funcionalidades, veja [APRESENTACAO_CLIENTE.md](APRESENTACAO_CLIENTE.md)**

## 🎯 O que é?

O sistema faz:

✅ **Sincroniza pedidos** da API externa automaticamente (2x ao dia às 11:29 e 21:00)  
✅ **Fluxo completo** de produção: Triagem → Produção → Rotulagem → Conferência → Expedição  
✅ **Gamificação** com pontos por atividade, bônus em dinheiro por faixas de desempenho  
✅ **Validação automática** com checklists obrigatórios antes de avançar etapa  
✅ **Controle de Qualidade** independente com formulários customizáveis  
✅ **Rastreamento completo** de cada fórmula e funcionário  
✅ **WebSockets** para notificações em tempo real  
✅ **APScheduler** para sincronizações automáticas  

---

## 🎮 Sistema de Pontuação

O sistema oferece três mecanismos de incentivo:

### 1️⃣ **Pontuação por Atividade** (Modelo PontuacaoPorAtividade)
Pontos automáticos por completar etapas, baseado em:
- **Atividade** (etapa do fluxo)
- **Produto** (fórmula específica)
- **Faixa de Quantidade** (até 100, 101-500, 500+)

Cada combinação pode ter pontuação diferente.

### 2️⃣ **Bônus em Dinheiro** (BonusFaixa)
Bônus **fixo e mensal** por faixa de desempenho:
- Até 400 pts: R$ 0
- 401-600 pts: R$ 150
- 601-900 pts: R$ 300
- 901-1200 pts: R$ 500
- 1201+ pts: R$ 800

### 3️⃣ **Pontuação Fixa Mensal** (PontuacaoFixaMensal)
- **Automática**: Por cada etapa concluída
- **Manual**: Gerenciador pode dar pontos extras ou penalidades com justificativa

### ❌ Penalizações (Penalizacao)
Aplicadas **manualmente** pelo gerente com motivo de justificativa.

---

## 📋 Requisitos

- **Local**: Python 3.11+, Redis, pip
- **Render**: PostgreSQL, Redis (Render for Redis)

## 🚀 Instalação Local

### 1. Clone ou extraia o projeto

```bash
cd farmacianovo
```

### 2. Crie um ambiente virtual (recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edite o arquivo `.env` e configure:

```env
SECRET_KEY=gere-uma-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://127.0.0.1:6379/0
```

Para gerar uma SECRET_KEY segura:

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Execute as migrações do banco de dados

```bash
python manage.py migrate
```

### 6. Configure o sistema inicial

```bash
python manage.py setup_inicial
```

Cria:
- Grupos de usuários (Superadmin, Gerente, Funcionário)
- Etapas do workflow
- Configurações de pontuação
- Faixas de bônus

### 7. Crie um superusuário

```bash
python manage.py createsuperuser
```

### 8. (Opcional) Crie pedidos de teste

```bash
python manage.py criar_pedidos_teste
```

### 9. Inicie o servidor

```bash
# Servidor Django padrão
python manage.py runserver

# Ou com Daphne (para WebSockets)
daphne -b 0.0.0.0 -p 8000 producao_gamificada.asgi:application
```

### 10. Sincronize com a API Externa (Uma vez)

```bash
python manage.py sincronizar_formulas_api
```

Este comando:
- ✅ Busca todos os pedidos da API externa
- ✅ Cria/atualiza fórmulas e itens
- ✅ Sincroniza datas e horas (DTALT + HRALT) em `datetime_atualizacao_api`
- ✅ Ordena formulas por data mais recente primeiro

**Após iniciar o servidor, a sincronização ocorre automaticamente:**
- 🔄 Diariamente às **11:29** da manhã
- 🔄 Diariamente às **21:00** da noite

Configure em: `core/scheduler.py` se precisar mudar os horários.

---

## 🌐 Deploy no Render (com SQLite)

### Pré-requisitos

1. Conta no [Render.com](https://render.com)
2. Projeto no GitHub
3. Arquivo `db.sqlite3` localmente com os dados

### Passo 1: Prepare o Repositório

1. Certifique-se que o `db.sqlite3` está no repositório:

```bash
# Verifique se está no .gitignore
cat .gitignore | grep sqlite3

# Se estiver, remova a linha
# Edite .gitignore e remova: *.sqlite3 ou db.sqlite3
```

2. Adicione o banco de dados ao Git:

```bash
git add db.sqlite3
git commit -m "Add database with initial data"
git push origin main
```

### Passo 2: Crie um arquivo `render.yaml`

Na raiz do projeto:

```yaml
services:
  - type: web
    name: farmacianovo
    env: python
    plan: free
    buildCommand: >
      pip install -r requirements.txt &&
      python manage.py collectstatic --noinput
    startCommand: >
      daphne -b 0.0.0.0 -p $PORT producao_gamificada.asgi:application
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: false
      - key: ALLOWED_HOSTS
        value: "*.render.com"
      - key: REDIS_URL
        fromService:
          name: farmacianovo-redis
          property: connectionString

  - type: redis
    name: farmacianovo-redis
    plan: free
    ipAllowList: []
```

### Passo 3: Push para GitHub

```bash
git add .
git commit -m "Deploy preparation for Render"
git push origin main
```

### Passo 4: Deploy no Render

1. Acesse [Render Dashboard](https://dashboard.render.com)
2. Clique em **"New +"** → **"Blueprint"**
3. Conecte seu repositório GitHub (`tarcisions/farmacianovo`)
4. Selecione a branch `main`
5. Clique em **"Deploy"**

Render vai criar automaticamente:
- Serviço Web (Daphne)
- Redis
- Usar o `db.sqlite3` do repositório

### Passo 5: Configure Variáveis de Ambiente

No dashboard do Render:
1. Vá para seu serviço web
2. Em **"Environment"**, verifique:

```
SECRET_KEY=<gerado automaticamente>
DEBUG=false
ALLOWED_HOSTS=seu-app.render.com
REDIS_URL=<configurado automaticamente>
```

### 🚀 Seu App Estará Online!

Acesse: `https://seu-app.render.com`

---

## ⚠️ Importante: Persistência de Dados

### SQLite no Render

SQLite funciona, mas **os dados serão perdidos** quando o app reiniciar (plano free do Render reinicia regularmente).

**Opções:**

1. **Aceitar a perda de dados** (ok para testes)
2. **Fazer backup do DB localmente:**
   ```bash
   # Faça isso regularmente
   git pull
   # db.sqlite3 será atualizado se alguém fez mudanças
   ```

3. **Usar PostgreSQL grátis** (melhor para produção - dados persistem)

---

## 📝 Configuração do `.env`

```env
# Django
SECRET_KEY=sua-chave-secreta-segura
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,seu-app.render.com

# Banco de Dados
DATABASE_URL=sqlite:///db.sqlite3  # Local
# DATABASE_URL=postgresql://user:pass@host/dbname  # Render

# Redis
REDIS_URL=redis://127.0.0.1:6379/0  # Local
# REDIS_URL=redis://:password@host:port  # Render

# Email (opcional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-app
```

---

## 🛠️ Troubleshooting

### "ModuleNotFoundError: No module named 'django'"
```bash
pip install -r requirements.txt
```

### Redis não conecta no Render
- Verifique a URL do Redis no dashboard
- Certifique-se que `REDIS_URL` está configurada corretamente

### Banco de dados vazio após deploy
Execute no shell do Render:
```bash
python manage.py migrate
python manage.py setup_inicial
```

### Static files não aparecem
No shell do Render:
```bash
python manage.py collectstatic --noinput
```

---

## 📚 Estrutura do Projeto

```
farmacianovo/
├── core/                    # App principal
├── dashboard/               # Dashboard
├── workflow/                # Gerenciamento de etapas
├── gamification/            # Sistema de pontuação
├── producao_gamificada/     # Settings e config
├── templates/               # Templates HTML
├── static/                  # Arquivos estáticos
├── db.sqlite3               # Banco local
├── manage.py
└── requirements.txt
```

Acesse: http://127.0.0.1:8000

## 🔧 Configuração do Redis

O sistema utiliza Redis para:
- Channels (WebSocket)
- Celery (tarefas assíncronas)

### Instalação do Redis

**Windows:**
- Baixe o Redis para Windows: https://github.com/microsoftarchive/redis/releases
- Ou use WSL2 e instale via apt

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

### Verificar se o Redis está rodando

```bash
redis-cli ping
```

Deve retornar: `PONG`

## 📦 Estrutura do Projeto

```
projeto_export/
├── core/                   # App principal com models
├── dashboard/              # Dashboards e views principais
├── gamification/           # Sistema de gamificação
├── workflow/               # Gestão de etapas e workflow
├── producao_gamificada/    # Configurações do projeto
├── templates/              # Templates HTML
├── static/                 # Arquivos estáticos (CSS, JS, imgs)
├── manage.py               # Gerenciador Django
└── requirements.txt        # Dependências Python
```

## 👥 Tipos de Usuário

1. **Superadmin**: Acesso total ao sistema
2. **Gerente**: Visualiza dashboards, gerencia funcionários
3. **Funcionário**: Trabalha em pedidos e acumula pontos

## 🎮 Funcionalidades

### Para Funcionários
- ✅ Assumir pedidos disponíveis automaticamente sincronizados
- ✅ Avançar entre etapas: Triagem → Produção → Rotulagem → Conferência → Expedição
- ✅ Completar checklists obrigatórios antes de avançar
- ✅ Responder perguntas de Controle de Qualidade quando necessário
- ✅ Visualizar pontuação em tempo real no painel
- ✅ Histórico de toda produção realizada

### Para Gerentes
- ✅ Dashboard visual com métricas de produção
- ✅ Ranking em tempo real de funcionários por pontuação mensal
- ✅ Visualização de fórmulas em cada etapa do workflow
- ✅ Aplicar penalizações manuais com justificativa
- ✅ Relatórios de desempenho e pontuação
- ✅ Gerenciar configurações de pontuação e checklists

### Para Superadmins
- ✅ Todas as funcionalidades de gerentes
- ✅ Gerenciamento completo de usuários
- ✅ Configuração de etapas do workflow
- ✅ Definição de pontos por atividade e faixa de quantidade
- ✅ Configuração de faixas de bônus em dinheiro
- ✅ Gestão de perguntas e respostas de QC
- ✅ Acesso ao painel administrativo Django

## � Sincronização Automática com API

O sistema sincroniza automaticamente com a API externa usando **APScheduler**:

| Horário | Tarefa |
|---------|--------|
| 11:29 | Sincroniza pedidos, prices, quantidades, datas e horas |
| 21:00 | Sincroniza novamente para manter dados atualizados |

**Dados sincronizados da API:**
- `DTALT` + `HRALT` → Combinados em `datetime_atualizacao_api` (com índice para performance)
- `QUANT` → Quantidade do item
- `PRUNI` → Preço unitário
- `VRTOT` → Valor total
- `DESCRICAOWEB` → Descrição para exibição

**Localização do agendador:** `core/scheduler.py`

---

## �🔐 Primeiro Acesso

1. Acesse: http://127.0.0.1:8000/admin
2. Faça login com o superusuário criado
3. Crie funcionários e gerentes
4. Atribua os grupos corretos aos usuários
5. Configure as etapas e pontuações conforme necessário

## 📊 Comandos Úteis

```bash
# Criar superusuário
python manage.py createsuperuser

# Executar migrações
python manage.py migrate

# Criar migrações após alterar models
python manage.py makemigrations

# Coletar arquivos estáticos
python manage.py collectstatic

# Sincronizar com API externa (manual)
python manage.py sincronizar_formulas_api

# Criar pedidos de teste
python manage.py criar_pedidos_teste

# Rodar testes
python manage.py test

# Shell interativo do Django
python manage.py shell

# Limpar dados temporários
python manage.py limpar_formulas --confirmar
```

## 🐛 Troubleshooting

### Erro: "No module named 'channels'"
```bash
pip install -r requirements.txt
```

### Erro: "Redis connection refused"
Certifique-se de que o Redis está rodando:
```bash
redis-cli ping
```

### Erro: "SECRET_KEY not found"
Crie o arquivo `.env` baseado no `.env.example`

### Porta 8000 já está em uso
```bash
python manage.py runserver 8080
```

## 📝 Notas Importantes

- ✅ **APScheduler está ativo** - A sincronização com API ocorre automaticamente 2x por dia
- Se precisar sincronizar manualmente: `python manage.py sincronizar_formulas_api`
- O banco de dados SQLite já vem com dados de exemplo se você copiou o `db.sqlite3`
- Para produção, configure um banco PostgreSQL ou MySQL
- Altere `DEBUG=False` em produção
- Configure `ALLOWED_HOSTS` com seu domínio em produção
- Use um servidor ASGI como Daphne ou Uvicorn em produção
- WebSockets (Channels) requer Redis configurado para notificações em tempo real

## 🆘 Suporte

Para problemas ou dúvidas:
1. Verifique os logs do Django
2. Consulte a documentação oficial do Django: https://docs.djangoproject.com/
3. Verifique os arquivos de log em `producao_gamificada/`

## 📄 Licença

Este projeto é proprietário.

---

**Versão:** 1.0.0  
**Data de Export:** 21/11/2025 17:42:51
