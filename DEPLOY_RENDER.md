# 🚀 Guia Rápido: Deploy no Render

## Resumo
Deploy simples usando SQLite existente + Redis do Render

## Passo 1: Prepare o Repositório

```bash
# Verifique se db.sqlite3 está no .gitignore
type .gitignore | find "sqlite3"

# Se estiver lá, remova a linha de *.sqlite3 no .gitignore
```

## Passo 2: Adicione o Banco ao Git

```bash
git add db.sqlite3 .env.example render.yaml
git commit -m "Setup for Render deployment with SQLite"
git push origin main
```

## Passo 3: Deploy no Render

1. Abra [render.com](https://render.com)
2. Faça login com GitHub
3. Clique em **"New +"** → **"Blueprint"**
4. Selecione repositório: `tarcisions/farmacianovo`
5. Branch: `main`
6. Clique em **"Deploy"**

## Passo 4: Pronto! 🎉

Render vai criar:
- **Web Service** (Daphne na porta $PORT)
- **Redis** (para WebSockets e Celery)

URL: `https://farmacianovo.render.com`

## ℹ️ Informações Importantes

### SQLite no Render
- ✅ Funciona perfeitamente
- ⚠️ Dados podem ser perdidos quando o app reinicia (plano free)
- ✅ Novo deploy = novos dados do `db.sqlite3` do repositório

### Para Manter Dados Entre Deploys
1. Faça pull do repositório regularmente
2. Se alterar dados, faça:
   ```bash
   git add db.sqlite3
   git commit -m "Update database"
   git push
   ```
3. Redeploy no Render

### Variáveis de Ambiente
O Render cria automaticamente:
- `SECRET_KEY` (gerada aleatoriamente)
- `REDIS_URL` (conecta ao Redis criado)

Você só precisa verificar em "Settings" → "Environment"

### URLs Importantes
- **App**: `https://seu-app.render.com`
- **Admin Django**: `https://seu-app.render.com/admin`
- **Dashboard**: `https://seu-app.render.com/dashboard`

### Troubleshooting

#### App não inicia
```bash
# Verifique os logs no Render dashboard
# Procure por erros relacionados ao Redis ou banco
```

#### Redis não conecta
```bash
# O Render cria a URL automaticamente
# Ela já vem setada em REDIS_URL
# Apenas aguarde o Redis inicializar (pode levar 1-2 min)
```

#### Static files não aparecem
```bash
# Render executa collectstatic no build
# Se não funcionar, limpe o cache: New Deployment
```

## 📚 Mais Informações

Veja `README.md` para instruções de instalação local e mais detalhes.
