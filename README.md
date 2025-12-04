# Sistema de Produção Gamificada

Sistema web completo de gestão de produção com gamificação para funcionários.

## 📋 Requisitos

- Python 3.11 ou superior
- Redis (para Celery e Channels)
- pip (gerenciador de pacotes Python)

## 🚀 Instalação Local

### 1. Clone ou extraia o projeto

```bash
cd projeto_export
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

Copie o arquivo `.env.example` para `.env` e configure:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edite o arquivo `.env` e altere a `SECRET_KEY`:

```
SECRET_KEY=gere-uma-chave-secreta-aqui
```

Para gerar uma SECRET_KEY segura, execute:

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Execute as migrações do banco de dados

```bash
python manage.py migrate
```

### 6. Configure o sistema inicial

Execute o comando para criar etapas, grupos e configurações:

```bash
python manage.py setup_inicial
```

Este comando criará:
- Grupos de usuários (Superadmin, Gerente, Funcionário)
- Etapas do workflow
- Configurações de pontuação
- Faixas de bônus

### 7. Crie um superusuário

```bash
python manage.py createsuperuser
```

Siga as instruções para criar seu usuário administrador.

### 8. (Opcional) Crie pedidos de teste

```bash
python manage.py criar_pedidos_teste
```

### 9. Inicie o servidor

```bash
python manage.py runserver
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
- Assumir e trabalhar em pedidos
- Completar checklists
- Registrar produções
- Registrar expedições (Sedex e Motoboy)
- Visualizar pontuação e histórico

### Para Gerentes
- Dashboard com métricas de produção
- Ranking de funcionários
- Gestão de penalizações
- Relatórios exportáveis

### Para Superadmins
- Todas as funcionalidades
- Gestão de usuários
- Configuração de etapas
- Configuração de pontuações e bônus

## 🔐 Primeiro Acesso

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

# Criar pedidos de teste
python manage.py criar_pedidos_teste

# Rodar testes
python manage.py test

# Shell interativo do Django
python manage.py shell
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

- O banco de dados SQLite já vem com dados de exemplo se você copiou o `db.sqlite3`
- Para produção, configure um banco PostgreSQL ou MySQL
- Altere `DEBUG=False` em produção
- Configure `ALLOWED_HOSTS` com seu domínio em produção
- Use um servidor ASGI como Daphne ou Uvicorn em produção

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
