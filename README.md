# English Learning Multi-Agent App 🎓

Um aplicativo web avançado para aprendizado de inglês americano utilizando sistema multi-agente com IA. Foco em 4 pilares: **Vocabulário**, **Gramática**, **Pronúncia** e **Conversação**.

## 🎯 Visão Geral

Este aplicativo utiliza uma arquitetura de **9 agentes especializados** coordenados por **LangGraph** para proporcionar uma experiência de aprendizado personalizada, científica e eficaz.

### Pilares de Aprendizado

1. **📚 Vocabulário**
   - 2000 palavras mais comuns do inglês americano
   - Vocabulário técnico (engenharia de dados e IA)
   - Sistema de Repetição Espaçada (SRS) baseado em algoritmo SM-2
   - Rastreamento de uso e revisões automáticas

2. **✏️ Gramática**
   - Estudo ativo: explique as regras com suas palavras
   - Comparação com português (sua língua materna)
   - Validação de compreensão via GPT-4
   - Exercícios práticos contextualizados

3. **🎤 Pronúncia**
   - Técnica Shadowing (escutar e repetir)
   - Validação rigorosa via Azure Speech Services **SEM filtros**
   - Sons problemáticos (fonemas que não existem em português)
   - Feedback visual de posicionamento da boca

4. **💬 Conversação (Fala)**
   - Conversação em tempo real via WebSocket
   - Detecção automática de erros (gramática + pronúncia)
   - Geração automática de atividades corretivas
   - Fluxo natural (sem correções imediatas)

## 🏗️ Arquitetura Multi-Agente

### Agentes Principais

1. **Orchestrator Agent** - Coordena todos os agentes usando LangGraph
2. **Assessment Agent** - Avaliação inicial e contínua
3. **Vocabulary Agent** - Gerencia vocabulário e SRS
4. **Grammar Agent** - Ensino de gramática com comparação PT-EN
5. **Pronunciation Agent** - Validação de pronúncia via Azure Speech
6. **Speaking Agent** - Conversação em tempo real
7. **Scheduler Agent** - Sistema de revisão espaçada
8. **Error Integration Agent** - Detecta erros e gera atividades
9. **Progress Agent** - Rastreia métricas e progresso

### Fluxo de Comunicação

```
Usuário → Frontend (React) → API REST/WebSocket → Orchestrator Agent
                                                        ↓
                              [Seleciona agente baseado em contexto]
                                                        ↓
                        Vocabulary/Grammar/Pronunciation/Speaking Agent
                                                        ↓
                                Error Integration Agent (se erros)
                                                        ↓
                                    Progress Agent
                                                        ↓
                                   Scheduler Agent
                                                        ↓
                              Retorna próxima atividade
```

## 🛠️ Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Framework web moderno e rápido
- **LangGraph** - Orquestração de multi-agentes
- **Azure OpenAI** - GPT-4 para geração de conteúdo
- **Azure Speech Services** - Reconhecimento e síntese de voz
- **Azure Cosmos DB** - Banco de dados NoSQL
- **Pydantic** - Validação de dados

### Frontend
- **React 18+**
- **TypeScript**
- **Vite** - Build tool
- **TailwindCSS + DaisyUI** - Estilização
- **Redux Toolkit** - Gerenciamento de estado
- **Socket.io** - Comunicação em tempo real
- **Recharts** - Gráficos e visualizações

### Cloud
- **Microsoft Azure**
  - Azure OpenAI Service
  - Azure Cognitive Services (Speech)
  - Azure Cosmos DB
  - Azure App Service (deploy)

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.11+
- Node.js 18+
- Conta Azure com os seguintes recursos:
  - Azure OpenAI Service
  - Azure Speech Services
  - Azure Cosmos DB

### 1. Clone o Repositório

```bash
git clone <repository-url>
cd "Agents (Udemy)"
```

### 2. Configuração do Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais Azure
```

### 3. Configuração do Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Criar arquivo .env
echo "VITE_API_URL=http://localhost:8000" > .env
```

### 4. Configurar Recursos Azure

#### 4.1 Azure OpenAI

1. Acesse [Azure Portal](https://portal.azure.com)
2. Crie um recurso "Azure OpenAI"
3. Deploy do modelo GPT-4
4. Copie a **API Key** e **Endpoint** para o `.env`

#### 4.2 Azure Speech Services

1. Crie um recurso "Speech Services"
2. Copie a **Key** e **Region** para o `.env`

#### 4.3 Azure Cosmos DB

1. Crie uma conta Cosmos DB (API: Core SQL)
2. Crie um banco de dados: `english_learning_db`
3. Crie os containers (partition key: `/partitionKey`):
   - `users`
   - `vocabulary_progress`
   - `grammar_progress`
   - `pronunciation_progress`
   - `activities`
   - `speaking_sessions`
   - `schedule`
4. Copie **Endpoint** e **Primary Key** para o `.env`

### 5. Executar a Aplicação

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Acesse: `http://localhost:5173`

## 📁 Estrutura do Projeto

```
.
├── backend/
│   ├── app/
│   │   ├── agents/              # 9 agentes especializados
│   │   ├── services/            # Integrações Azure
│   │   ├── models/              # Modelos Pydantic
│   │   ├── api/v1/endpoints/    # API REST endpoints
│   │   ├── core/                # Segurança, WebSocket
│   │   ├── utils/               # SRS, processamento
│   │   ├── data/                # Dados iniciais (palavras, regras, sons)
│   │   ├── config.py            # Configurações centralizadas
│   │   └── main.py              # FastAPI entry point
│   ├── tests/                   # Testes
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Componentes React por pilar
│   │   ├── pages/               # Páginas principais
│   │   ├── services/            # API, WebSocket, áudio
│   │   ├── store/               # Redux state management
│   │   └── hooks/               # Custom hooks
│   └── package.json
│
├── infrastructure/
│   └── azure/
│       ├── bicep/               # Templates IaC
│       └── scripts/             # Scripts de deploy
│
└── docs/                        # Documentação
```

## 🎓 Funcionalidades Principais

### Sistema de Repetição Espaçada (SRS)

Implementa o algoritmo **SM-2** (SuperMemo 2):
- Primeira revisão: 1 dia
- Segunda revisão: 6 dias
- Revisões subsequentes: intervalo * ease_factor
- Ajuste automático baseado em performance

### Triggers de Revisão

1. **SRS Due**: `next_review <= hoje`
2. **Baixa Frequência**: não usado nos últimos 7 dias
3. **Baixo Score**: accuracy < 80%

### Níveis de Aprendizado

**Iniciante:**
- 2000 palavras mais comuns
- Vocabulário técnico básico
- Sons individuais (fonemas isolados)
- Gramática fundamental
- Conversação estruturada

**Intermediário:**
- Vocabulário avançado
- Conexão entre sons (linking, reduction)
- Variedade de sotaques (americano + britânico)
- Foco em listening
- Conversação avançada

### Integração Entre Pilares

Erros detectados durante conversação geram automaticamente atividades corretivas:
- Erro gramatical → Cria atividade no pilar **Gramática**
- Erro de pronúncia → Cria atividade no pilar **Pronúncia**

## 📊 API Endpoints

### Autenticação
- `POST /api/v1/users/register` - Registro de usuário
- `POST /api/v1/users/login` - Login

### Avaliação
- `POST /api/v1/assessment/initial` - Assessment inicial
- `POST /api/v1/assessment/continuous` - Avaliação contínua

### Vocabulário
- `GET /api/v1/vocabulary/next-activity` - Próxima atividade
- `POST /api/v1/vocabulary/submit-answer` - Submeter resposta

### Gramática
- `GET /api/v1/grammar/next-lesson` - Próxima lição
- `POST /api/v1/grammar/submit-explanation` - Submeter explicação

### Pronúncia
- `GET /api/v1/pronunciation/next-exercise` - Próximo exercício
- `POST /api/v1/pronunciation/submit-audio` - Submeter áudio

### Conversação
- `POST /api/v1/speaking/start-session` - Iniciar sessão
- `WS /api/v1/speaking/conversation` - WebSocket de conversação

### Progresso
- `GET /api/v1/progress/dashboard/{user_id}` - Dashboard de progresso
- `GET /api/v1/schedule/{user_id}/today` - Revisões do dia

## 🧪 Testes

```bash
# Backend
cd backend
pytest

# Com cobertura
pytest --cov=app --cov-report=html

# Frontend
cd frontend
npm test
```

## 📈 Monitoramento e Custos

### Custos Estimados (Azure)

Para ~100 usuários ativos/mês:
- **Cosmos DB**: $50-100/mês
- **Azure OpenAI (GPT-4)**: $200-500/mês
- **Azure Speech Services**: $100-200/mês
- **Total**: ~$350-800/mês

### Performance Targets

- API response time: < 200ms (p95)
- WebSocket latency: < 100ms
- Speech-to-Text processing: < 500ms

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está licenciado sob a licença MIT.

## 📧 Contato

Para dúvidas ou sugestões, abra uma issue no repositório.

---

**Desenvolvido com ❤️ utilizando Azure AI e LangGraph**
