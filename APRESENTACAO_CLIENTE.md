# 📊 Sistema de Produção Gamificada - Apresentação do Projeto

---

## 📌 Visão Geral

O **Sistema de Produção Gamificada** é uma plataforma web inovadora desenvolvida para otimizar e gerenciar o fluxo de produção de formulações farmacêuticas, integrando **gamificação** para aumentar a motivação e produtividade dos funcionários.

**Tecnologias:** Django 4.x, PostgreSQL, Redis, WebSockets (Channels), Bootstrap 5  
**Objetivo:** Automatizar o workflow de produção com rastreamento real-time e sistema de pontuação por desempenho

---

## 🎮 Sistema de Gamificação

### Como Funciona

O sistema **premia funcionários por desempenho** através de um sistema de pontos que considera:

#### 1️⃣ **Pontuação por Atividade**
- **Pontos por Tipo de Produto/Atividade**: Cada atividade (pesagem, encapsulação, análise, rotulagem, conferência) em cada tipo de produto ganha pontos configuráveis
  - Exemplo: Encapsular cápsula de 60 unidades = 5 pontos
  - Exemplo: Análise de líquido = 8 pontos
  - Valores configuráveis por faixa de quantidade (0-60, 60-120, etc.)

#### 2️⃣ **Bônus por Faixa de Pontos**
- Funcionários recebem **bônus em dinheiro** conforme pontos ganhos no mês
  - Até 400 pontos: R$ 0
  - 401-600 pontos: R$ 150
  - 601-800 pontos: R$ 250
  - Acima de 800: R$ 350 (teto)
  - Configurável por admin conforme política

#### 3️⃣ **Pontuação Fixa Mensal**
- Regras automáticas ou manuais de pontuação
  - Exemplo: 200 pontos por organização de estoque
  - Exemplo: 15 pontos por rota de motoboy
  - Configuráveis por etapa

#### 4️⃣ **Penalizações Manuais**
- Gerente pode aplicar descontos de pontos por infrações
  - Descontos registrados com justificativa
  - Pode ser revertidas

#### 5️⃣ **Ranking em Tempo Real**
- Dashboard mostra **Top 10 funcionários** do mês
- Incentiva competição saudável entre times

---

## 🔄 Fluxo de Produção (Início ao Fim)

### Etapas do Workflow

```
┌─────────────┐
│ 1. TRIAGEM  │  ← Sistema recebe pedido da API
└──────┬──────┘
       │ Checklist de análise
       ▼
┌─────────────────────┐
│ 2. PRODUÇÃO         │  ← Formulação e preparação
└──────┬──────────────┘
       │ Validação de checklists
       ▼
┌─────────────────────┐
│ 3. ROTULAGEM        │  ← Identificação do produto
└──────┬──────────────┘
       │ Checklist de rotulagem
       ▼
┌─────────────────────┐
│ 4. CONFERÊNCIA      │  ← Verificação final
└──────┬──────────────┘
       │ Checklist de conferência
       ▼
┌─────────────────────┐
│ 5. EXPEDIÇÃO        │  ← Saída do produto
└─────────────────────┘
```

### Ciclo de Uma Fórmula

1. **Sincronização de API** → Sistema importa novos pedidos (DTALT + HRALT)
2. **Triagem** → Analista revisa especificações (obrigatório marcar checklist)
3. **Produção** → Técnico manipula a fórmula conforme protocolo
4. **Rotulagem** → Preparação de rótulos e identificação
5. **Conferência** → Verificação final antes de sair
6. **Expedição** → Escolhe entre Motoboy (local) ou Sedex (correios)

---

## 📋 Controle de Qualidade

O **Controle de Qualidade é independente do fluxo** de produção:
- Funcionário preenche **formulário de QC** conforme necessário
- Sistema registra respostas às perguntas de qualidade
- Não bloqueia o avanço de etapas
- Rastreamento completamente separado

---

## 👥 Sistema de Permissões e Diferentes Perfis

### 1. **FUNCIONÁRIO**
- Pode **assumir fórmulas** disponíveis
- Trabalha apenas em **suas fórmulas atribuídas**
- Vê **seu histórico pessoal** de pontuação
- Não pode ver dados de outros funcionários
- **Ações permitidas:**
  - Marcar checklists obrigatórios ✅
  - Finalizar etapa (se todos os checklists estiverem marcados)
  - Pausar tarefa ativa
  - Ver suas estatísticas de pontos

### 2. **GESTOR/SUPERVISOR**
- Visualização **completa de todas as fórmulas**
- Pode **auditar trabalho** de funcionários
- Acesso a **relatórios de produtividade**
- Gerencia **checklists do sistema**
- **Ações permitidas:**
  - Ver todas as fórmulas (modo auditoria)
  - Consultar histórico de etapas
  - Aplicar penalizações
  - Gerar relatórios
  - Criar novas etapas/checklists

### 3. **SUPERADMIN/ADMIN**
- Acesso **total ao sistema**
- Painel administrativo Django
- Configuração de: etapas, checklists, pontuação, permissões
- Sincronização manual da API
- Gestão de usuários e grupos
- **Ações permitidas:** Todas as funcionalidades

### 4. **VISUALIZADOR (Read-Only)**
- Apenas visualiza dashboards
- Não pode executar ações
- Útil para consultores/clientes

---

## ✅ Sistema de Checklists

### O que são Checklists?

Listas de verificação que **validam qualidade e conformidade** em cada etapa.

### Tipos

1. **Checklists Obrigatórios** 🔴
   - Devem ser marcados para **passar da etapa**
   - Se não marcar → Sistema bloqueia finalização
   - Exemplo: "Solução preparada corretamente?" (Produção)

2. **Checklists Opcionais** 🟡
   - Não bloqueiam progresso
   - Usados para rastreamento

### Fluxo de Checklist

```
Etapa iniciada
     ↓
Funcionário marca checklists obrigatórios
     ↓
Tenta finalizar etapa
     ↓
Sistema valida: Todos os obrigatórios foram marcados?
     ↓
✅ SIM → Etapa avança, próxima etapa começa
❌ NÃO → Sistema mostra erro, bloqueia progresso
```

### Exemplo: Checklist de Triagem
- ☐ Receita analisada
- ☐ Quantidade conferida
- ☐ Ingredientes disponíveis
- ☐ Sem restrições (OBRIGATÓRIO)

---

## 📊 Dashboard e Visualizações

### Para Funcionário
- **Minhas Fórmulas**: Fórmulas que assumiu (ativas e pendentes)
- **Fórmulas Disponíveis**: Novas fórmulas para assumir
- **Pontuação**: Pontos no mês, ranking pessoal
- **Histórico de Etapas**: Tempo gasto em cada fórmula

### Para Gestor
- **Gestão de Pedidos**: Lista completa com filtros
- **Fórmulas Disponíveis** (Auditoria): Visualização somente leitura de todas as fórmulas
- **Histórico de Pontos**: Ranking da equipe
- **Penalizações**: Aplicar descontos de pontos com justificativa
- **Controle de Qualidade**: Visualizar formulários preenchidos
- **Relatórios**: Análise de produtividade e histórico

---

## 🔐 Segurança e Auditoria

### Rastreamento
- **Log de Auditoria**: Todas as ações registradas com timestamp e usuário
- **Histórico de Etapas**: Quem trabalhou e quantos pontos ganhou
- **Histórico de Formulários**: Controle de qualidade rastreado completamente

### Validações
- Checklists **obrigatórios** bloqueiam avanço de etapa se não marcados
- Funcionário só vê suas próprias fórmulas (exceto gerentes)
- Penalizações registradas com justificativa

---

## 🔄 Sistema de Sincronização com API

O sistema **sincroniza automaticamente** com API externa de pedidos:

### Como Funciona

1. **Agendador** (APScheduler) dispara sincronização **2x ao dia** (11:29 e 21:00)
2. API retorna pedidos com campos:
   - `NRORC`: Número do pedido
   - `DTALT` + `HRALT`: Data e hora da última atualização
   - `DESCRICAOWEB`: Descrição da fórmula
   - `QUANT`, `PRUNI`, `VRTOT`: Quantidade, preço unit., valor total

3. Sistema **agrupa por NRORC** (um pedido = N fórmulas)
4. Cria `PedidoMestre` + `FormulaItem` no banco
5. **Salva datetime_atualizacao_api** para ordenação correta

### Resultado
- Fórmulas sempre **ordenadas por mais recente primeiro**
- Novos pedidos aparecem automático no dashboard

---

## 💰 Exemplo de Cálculo de Pontuação

### Cenário: Funcionário realiza encapsulação

**Configuração no Admin:**
- Atividade: Encapsulação
- Tipo Produto: Cápsula
- Faixa Quantidade: 50-100 unidades
- Pontos: 8 pontos por fórmula

**Execução:**
- Fórmula: Cápsula com 75 unidades
- Checklist: ✅ Marcado corretamente
- Atividade concluída sem penalidades

**Cálculo:**
```
Pontos Base (encapsular 75 unidades) = 8 pontos
Penalizações                          = 0
────────────────────────────────────────────────
TOTAL                                = 8 pontos
```

**Resultado:** Funcionário ganha 8 pontos + avança para próxima etapa

---

## 🛠️ Configurações Ajustáveis

### Admin pode configurar:

1. **Etapas**
   - Nome, sequência, se está ativa
   - Laboratório responsável
   - Se gera pontos, se possui checklists

2. **Checklists**
   - Por etapa, texto, obrigatório/opcional
   - Pontos por checklist marcado

3. **Pontuação por Atividade**
   - Atividades: Pesagem, Encapsulação, Análise, Rotulagem, Conferência
   - Faixas de quantidade (ex: 0-60, 60-120, 120+)
   - Pontos por fórmula para cada faixa

4. **Pontuação Fixa Mensal**
   - Regras automáticas ou manuais
   - Por étapa relacionada
   - Valor em pontos

5. **Faixas de Bônus**
   - Faixas de pontos acumulados no mês
   - Valor em reais para cada faixa
   - Configurável livremente

6. **Penalizações**
   - Aplicadas manualmente pelo gerente
   - Com motivo e justificativa

7. **Tipos de Produto**
   - Cápsula, Pó, Líquido, Cremes, etc.
   - Customizável conforme necessidade

8. **Configuração de Expedição**
   - Tipos de rota (Motoboy, Sedex)
   - Custos e prazos

---

## 📈 Métricas e Relatórios

Sistema gera/permite análise de:

- **Produtividade**: Pontos ganhos por funcionário por período
- **Ranking**: Pontuação mensal dos funcionários
- **Histórico**: Rastreamento completo de cada fórmula com funcionários envolvidos
- **Auditoria**: Tudo registrado com timestamp e usuário

---

## 🚀 Diferenciais do Sistema

✅ **Gamificação integrada** → Motiva equipe  
✅ **Real-time updates** → WebSockets para notificações  
✅ **Sincronização automática** → Sem entrada manual de dados  
✅ **Rastreamento completo** → Auditoria total  
✅ **Validação inteligente** → Checklists obrigatórios  
✅ **Escalável** → Funciona com N funcionários/fórmulas  
✅ **Intuitivo** → Interface limpa e responsiva  
✅ **Seguro** → Permissões granulares + logs  

---

## 📱 Dispositivos

- **Desktop**: Totalmente otimizado
- **Tablet**: Layout responsivo
- **Mobile**: Interface adaptada (não 100% mobile-friendly para confecção, recomenda desktop)

---

## 🔗 Integração com Sistemas

### Entrada (API)
- Sincroniza com sistema externo de pedidos
- Importa DTALT/HRALT para rastreamento

### Saída
- Logs exportáveis para auditoria
- Relatórios em PDF/Excel (futuro)

---

## 🎯 Casos de Uso Principais

### 1. Gerente Acompanha Produção
1. Abre dashboard
2. Vê todas as fórmulas em andamento
3. Clica em fórmula para auditar detalhes
4. Vê checklist marcado + histórico de funcionário
5. Aplica penalização se necessário

### 2. Funcionário Trabalha em Fórmula
1. Entra em "Fórmulas Disponíveis"
2. Clica em fórmula → Marca como assumida
3. Abre fórmula → Vê checklists obrigatórios
4. Marca cada checklist conforme trabalha
5. Clica "Finalizar Etapa" → Sistema valida
6. Etapa avança, ganhar pontos automaticamente
7. Próxima etapa começa

### 3. Controle de Qualidade
1. Funcionário clica em "Controle de Qualidade"
2. Preenche formulário com identificação do item
3. Responde perguntas obrigatórias do formulário
4. Sistema registra respostas + timestamp
5. Histórico disponível para auditoria posterior

---

**Data de Elaboração:** 04/03/2026  
**Versão do Sistema:** 4.0 (Django)  
**Status:** ✅ Produção  

---

*Documento preparado para apresentação ao cliente final.*
