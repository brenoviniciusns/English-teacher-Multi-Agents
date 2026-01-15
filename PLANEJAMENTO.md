✅ O que está coberto no plano:
Arquitetura
9 agentes especializados coordenados por LangGraph
4 pilares completos: Vocabulário, Gramática, Pronúncia e Fala
Integração entre pilares: erros em Speaking geram atividades em Grammar/Pronunciation
Funcionalidades Principais
SRS (Spaced Repetition) com algoritmo SM-2
2000 palavras mais comuns + vocabulário técnico (dados/IA)
Comparação PT-EN para gramática
Pronúncia rigorosa: Azure Speech sem filtros
Shadowing para pronúncia
Conversação em tempo real via WebSocket
2 níveis: Iniciante e Intermediário
Sistema de revisão automático (7 dias)
Transparência total: usuário sempre sabe seu progresso
Implementação
12 fases sequenciais de implementação
Estrutura completa de diretórios
Arquivos críticos identificados (15 arquivos principais)
Integrações Azure detalhadas (OpenAI, Speech, Cosmos DB)
10 testes end-to-end para verificação
Técnico
Backend: Python + FastAPI + LangGraph
Frontend: React + TypeScript
Cloud: Azure (Cosmos DB, OpenAI GPT-4, Speech Services)
Custos estimados: $350-800/mês
O plano está pronto para aprovação e execução! 🚀

Claude’s Plan
Plano de Implementação: Aplicativo Multi-Agente para Aprendizado de Inglês Americano
Visão Geral
Construir um aplicativo web completo para aprendizado de inglês americano com sistema multi-agente, focado em 4 pilares: Vocabulário, Gramática, Pronúncia e Fala. O sistema usa Azure (OpenAI, Speech Services, Cosmos DB) e arquitetura Python (FastAPI) + React.

Stack Tecnológica Confirmada
Backend: Python + FastAPI
Frontend: React + TypeScript
Orquestração: LangGraph (multi-agente)
Cloud: Azure (OpenAI GPT-4, Speech Services, Cosmos DB)
Interface: Web App (Browser)
Arquitetura Multi-Agente
Agentes Principais (9 agentes especializados)
Orchestrator Agent (LangGraph) - Coordena todos os agentes
Assessment Agent - Avaliação inicial e contínua
Vocabulary Agent - Gerencia vocabulário e SRS
Grammar Agent - Ensino de gramática com comparação PT-EN
Pronunciation Agent - Validação de pronúncia via Azure Speech
Speaking Agent - Conversação em tempo real
Scheduler Agent - Sistema de revisão espaçada (SRS)
Error Integration Agent - Detecta erros e gera atividades corretivas
Progress Agent - Rastreia métricas e progresso
Fluxo de Comunicação

Usuário → Frontend → API REST/WebSocket → Orchestrator Agent
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
Estrutura de Diretórios

c:\Projetos\Agents (Udemy)\
├── backend/
│   ├── app/
│   │   ├── main.py                          # FastAPI entry point
│   │   ├── config.py                        # Configurações e variáveis de ambiente
│   │   ├── core/
│   │   │   ├── security.py                  # Autenticação JWT
│   │   │   ├── dependencies.py              # FastAPI dependencies
│   │   │   └── websocket_manager.py         # Gerenciamento WebSocket
│   │   ├── agents/
│   │   │   ├── base_agent.py                # Classe base para agentes
│   │   │   ├── orchestrator.py              # LangGraph orchestrator
│   │   │   ├── assessment_agent.py
│   │   │   ├── vocabulary_agent.py
│   │   │   ├── grammar_agent.py
│   │   │   ├── pronunciation_agent.py
│   │   │   ├── speaking_agent.py
│   │   │   ├── scheduler_agent.py           # SRS implementation
│   │   │   ├── error_integration_agent.py
│   │   │   └── progress_agent.py
│   │   ├── services/
│   │   │   ├── azure_openai_service.py      # Azure OpenAI SDK
│   │   │   ├── azure_speech_service.py      # Azure Speech SDK
│   │   │   ├── cosmos_db_service.py         # Cosmos DB operations
│   │   │   └── cache_service.py             # Redis/in-memory cache
│   │   ├── models/                          # Pydantic models
│   │   ├── schemas/                         # API schemas
│   │   ├── api/v1/endpoints/                # API endpoints
│   │   ├── utils/
│   │   │   ├── srs_algorithm.py             # Spaced Repetition (SM-2)
│   │   │   ├── phonetic_analyzer.py
│   │   │   └── text_processor.py
│   │   └── data/
│   │       ├── common_words_2000.json       # 2000 palavras mais comuns
│   │       ├── technical_vocabulary.json    # Vocabulário técnico (dados/IA)
│   │       ├── grammar_rules.json           # Regras gramaticais
│   │       └── phonetic_sounds.json         # Sons não existentes em PT
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── common/                      # Componentes reutilizáveis
│   │   │   ├── vocabulary/
│   │   │   ├── grammar/
│   │   │   ├── pronunciation/
│   │   │   └── speaking/
│   │   ├── pages/
│   │   ├── services/
│   │   │   ├── api.ts                       # Cliente API
│   │   │   ├── websocket.ts                 # Cliente WebSocket
│   │   │   └── audio.ts                     # Gravação/playback
│   │   ├── store/                           # Redux/Zustand
│   │   └── hooks/
│   ├── package.json
│   └── Dockerfile
│
├── infrastructure/
│   └── azure/
│       ├── bicep/                           # Templates Azure
│       └── scripts/                         # Scripts de deploy
│
├── docs/
└── scripts/
    └── populate_initial_data.py             # Popular dados iniciais
Integrações Azure
1. Azure OpenAI (GPT-4)
Gerar exercícios de vocabulário contextualizados
Validar explicações de gramática do usuário
Conduzir conversações naturais (Speaking Agent)
Criar perguntas de avaliação adaptativas
2. Azure Speech Services
Speech-to-Text: Reconhecimento de pronúncia SEM filtros (importante!)
Text-to-Speech: Gerar áudio para shadowing
Pronunciation Assessment: Feedback detalhado fonético
3. Azure Cosmos DB (NoSQL)
Containers:

users - Perfil e nível do usuário
vocabulary_progress - Progresso de cada palavra + SRS
grammar_progress - Progresso de regras gramaticais + explicações
pronunciation_progress - Histórico de pronúncia por fonema
activities - Exercícios e atividades
speaking_sessions - Histórico de conversações
schedule - Revisões agendadas (SRS)
Partition Key: user_id para todos os containers

Funcionalidades Principais por Pilar
Pilar 1: Vocabulário
2000 palavras mais comuns do inglês americano
Vocabulário técnico: engenharia de dados + IA
SRS (Spaced Repetition System): Algoritmo SM-2
Rastreamento de uso: últimos 7 dias
Auto-agendamento: palavras não usadas → revisão
Exercícios contextualizados: gerados por GPT-4
Pilar 2: Gramática
Estudo ativo: usuário explica a regra com suas palavras
Comparação PT-EN: identificar se regra existe em português
Validação via GPT-4: avaliar compreensão do usuário
Exercícios práticos: frases para aplicar a regra
Base de ~100 regras gramaticais
Pilar 3: Pronúncia
Técnica Shadowing: escutar e repetir
Validação rigorosa: Azure Speech sem filtros
Sons problemáticos: fonemas que não existem em PT (ex: /θ/, /ð/)
Feedback visual: posicionamento da boca
Accuracy mínimo: 85% para considerar dominado
Pilar 4: Fala (Conversação)
Conversação em tempo real: via WebSocket
Detecção de erros: gramática + pronúncia
Geração automática de atividades:
Erro gramatical → cria atividade no pilar Gramática
Erro de pronúncia → cria atividade no pilar Pronúncia
Fluxo natural: agente NÃO corrige imediatamente
Feedback pós-conversação: resumo de erros
Níveis de Aprendizado
Iniciante
2000 palavras mais comuns
Vocabulário técnico básico
Sons individuais (fonemas isolados)
Gramática fundamental
Conversação estruturada
Intermediário
Vocabulário avançado
Conexão entre sons: como nativos juntam palavras
Variedade: sotaques (americano + britânico), idades, estilos
Foco em listening: mais tempo ouvindo
Conversação avançada: tópicos complexos
Sistema de Revisão (SRS)
Algoritmo SM-2 (Spaced Repetition)

- Se correto: intervalo aumenta (1 → 6 → intervalo * ease_factor)
- Se incorreto: intervalo volta para 1 dia
- ease_factor: ajustado baseado em qualidade da resposta
Triggers de Revisão
SRS due: next_review <= hoje
Baixa frequência: não usado nos últimos 7 dias
Baixo score: accuracy < 80%
Schedule Diário
Criado automaticamente pelo Scheduler Agent
Respeita daily_goal_minutes do usuário
Prioriza: SRS > Baixa frequência > Novos itens
Fluxos Críticos
Fluxo 1: Onboarding
Registro do usuário
Assessment Inicial:
20 palavras de vocabulário
5 regras de gramática
5 sons básicos
1 minuto de conversação
Determinação de nível: Iniciante ou Intermediário
Dashboard com plano personalizado
Fluxo 2: Sessão de Vocabulário
GET /api/v1/vocabulary/next-activity
Scheduler verifica SRS + frequência
Vocabulary Agent seleciona palavra
GPT-4 gera exercício contextualizado
Usuário responde
Progress Agent atualiza SRS
Recalcula next_review
Fluxo 3: Sessão de Pronúncia
GET /api/v1/pronunciation/next-exercise
Pronunciation Agent seleciona fonema (ex: /θ/)
Apresenta diagrama de boca
Text-to-Speech: gera áudio "think"
Usuário grava pronúncia (WebSocket)
Azure Speech: reconhecimento SEM filtros
Compara: detectado vs. esperado
Feedback detalhado: "Tongue position needs adjustment"
Se accuracy < 85%: permite 3 tentativas
Se ainda < 70%: agenda revisão
Fluxo 4: Sessão de Conversação (Speaking)
POST /api/v1/speaking/start-session
WebSocket mantém conexão aberta
Speaking Agent inicia: "What did you do this morning?"
Text-to-Speech: gera áudio
Usuário responde: grava áudio
Speech-to-Text: transcreve (sem filtros)
Error Integration Agent: detecta erros
Erro gramatical: "waked" → "woke"
Erro pronúncia: /θ/ → /s/
Speaking Agent continua conversa (fluxo natural)
Após 5-10 turnos: fim da sessão
Geração de atividades corretivas:
Erro "waked" → cria atividade Grammar
Erro /θ/ → cria atividade Pronunciation
Dashboard: mostra erros + atividades geradas
Fluxo 5: Avaliação Contínua
Trigger: a cada 5 sessões ou mudança de desempenho
Assessment Agent analisa métricas (últimas 2 semanas)
Decisões:
Upgrade: Iniciante → Intermediário
Manter nível
Revisar: identifica pilar fraco, aumenta frequência
Relatório detalhado ao usuário
Passos de Implementação
Fase 1: Setup & Infrastructure (Fundação)
Arquivos críticos a criar:

infrastructure/azure/bicep/main.bicep - Provisionamento Azure
backend/app/config.py - Configurações centralizadas
backend/requirements.txt - Dependências Python
frontend/package.json - Dependências React
backend/.env.example - Template de variáveis de ambiente
Tarefas:

Provisionar recursos Azure (Cosmos DB, OpenAI, Speech)
Criar estrutura de pastas completa
Setup FastAPI básico com CORS
Setup React + TypeScript + TailwindCSS
Configurar autenticação JWT básica
Criar schemas Cosmos DB (containers + partition keys)
Fase 2: Services & Data Layer (Integrações)
Arquivos críticos a criar:

backend/app/services/azure_openai_service.py - Cliente Azure OpenAI
backend/app/services/azure_speech_service.py - Cliente Azure Speech
backend/app/services/cosmos_db_service.py - Cliente Cosmos DB
backend/app/models/user.py - Modelo de usuário
backend/app/models/vocabulary.py - Modelo de vocabulário
backend/app/models/progress.py - Modelo de progresso
backend/app/utils/srs_algorithm.py - Algoritmo SM-2
Tarefas:

Implementar Azure OpenAI Service (chat completion)
Implementar Azure Speech Service (STT + TTS + Pronunciation Assessment)
Implementar Cosmos DB Service (CRUD operations)
Criar modelos Pydantic para todos os containers
Implementar algoritmo SRS (SM-2)
Criar scripts para popular dados iniciais (2000 palavras, regras, sons)
Fase 3: Core Agents (Orquestração)
Arquivos críticos a criar:

backend/app/agents/base_agent.py - Classe base
backend/app/agents/orchestrator.py - LangGraph orchestrator
backend/app/agents/assessment_agent.py - Avaliação
backend/app/agents/scheduler_agent.py - SRS scheduling
backend/app/agents/progress_agent.py - Progress tracking
Tarefas:

Implementar Base Agent com interface comum
Implementar Orchestrator Agent usando LangGraph:
Definir AppState (TypedDict)
Criar grafo de estados
Implementar conditional edges
Implementar Assessment Agent (initial + continuous)
Implementar Scheduler Agent (SRS logic)
Implementar Progress Agent (métricas e dashboards)
Testar orquestração básica
Fase 4: Vocabulary Pillar (Primeiro pilar completo)
Arquivos críticos a criar:

backend/app/agents/vocabulary_agent.py
backend/app/api/v1/endpoints/vocabulary.py
frontend/src/components/vocabulary/VocabularyCard.tsx
frontend/src/components/vocabulary/VocabularyExercise.tsx
frontend/src/pages/VocabularyPage.tsx
backend/app/data/common_words_2000.json
backend/app/data/technical_vocabulary.json
Tarefas:

Implementar Vocabulary Agent:
Seleção de palavra baseada em SRS
Geração de exercício via GPT-4
Validação de resposta
Atualização de progresso
Popular dados: 2000 palavras + vocabulário técnico
Criar API endpoints: /next-activity, /submit-answer, /progress
Implementar frontend: componentes de exercício e progresso
Integrar SRS completo para vocabulário
Testar fluxo end-to-end
Fase 5: Grammar Pillar
Arquivos críticos a criar:

backend/app/agents/grammar_agent.py
backend/app/api/v1/endpoints/grammar.py
frontend/src/components/grammar/GrammarLesson.tsx
frontend/src/components/grammar/ComparisonView.tsx
frontend/src/pages/GrammarPage.tsx
backend/app/data/grammar_rules.json
Tarefas:

Implementar Grammar Agent:
Apresentação de regra com comparação PT-EN
Validação de explicação do usuário via GPT-4
Geração de exercícios práticos
Armazenamento de explicações
Popular base de ~100 regras gramaticais
Criar API endpoints: /next-lesson, /submit-explanation, /submit-exercise
Implementar frontend: lição, comparação PT-EN, exercícios
Integrar SRS para gramática
Testar fluxo end-to-end
Fase 6: Pronunciation Pillar
Arquivos críticos a criar:

backend/app/agents/pronunciation_agent.py
backend/app/api/v1/endpoints/pronunciation.py
backend/app/core/websocket_manager.py
frontend/src/components/pronunciation/ShadowingExercise.tsx
frontend/src/components/pronunciation/MouthPositionGuide.tsx
frontend/src/hooks/useAudioRecorder.ts
frontend/src/services/websocket.ts
backend/app/data/phonetic_sounds.json
Tarefas:

Implementar Pronunciation Agent:
Seleção de fonema
Text-to-Speech para shadowing
Recepção de áudio via WebSocket
Speech-to-Text SEM filtros (crítico!)
Pronunciation Assessment detalhado
Feedback específico (tongue position, etc.)
Popular base de ~30 sons problemáticos (não existem em PT)
Setup WebSocket para streaming de áudio
Criar API endpoints + WebSocket endpoint
Implementar frontend:
Gravação de áudio (Web Audio API)
Diagrama de posicionamento de boca
Feedback visual de accuracy
Integrar Azure Speech Pronunciation Assessment
Testar fluxo end-to-end
Fase 7: Speaking Pillar & Error Integration
Arquivos críticos a criar:

backend/app/agents/speaking_agent.py
backend/app/agents/error_integration_agent.py
backend/app/api/v1/endpoints/speaking.py
frontend/src/components/speaking/ConversationInterface.tsx
frontend/src/components/speaking/ErrorHighlight.tsx
frontend/src/pages/SpeakingPage.tsx
Tarefas:

Implementar Speaking Agent:
Iniciar conversação (escolher tópico)
Manter contexto da conversa
Gerar respostas naturais via GPT-4
Text-to-Speech para respostas
Speech-to-Text para usuário
Detectar erros (gramatical + pronúncia)
Implementar Error Integration Agent:
Analisar erros detectados
Criar atividades em Grammar ou Pronunciation
Armazenar em Cosmos DB
Criar API endpoints: /start-session, /end-session, /conversation (WebSocket)
Implementar frontend:
Interface de conversação em tempo real
Highlight de erros pós-conversa
Lista de atividades geradas
Integração entre pilares: testar geração automática de atividades
Testar fluxo end-to-end completo
Fase 8: Progress Dashboard & Scheduling
Arquivos críticos a criar:

frontend/src/components/progress/ProgressDashboard.tsx
frontend/src/components/progress/PillarProgress.tsx
frontend/src/components/progress/ReviewSchedule.tsx
frontend/src/pages/Dashboard.tsx
backend/app/api/v1/endpoints/progress.py
Tarefas:

Criar dashboard de progresso:
Progresso por pilar (gráficos)
Nível atual e próximo nível
Revisões agendadas para hoje
Streak (dias consecutivos)
Implementar visualização de schedule diário/semanal
Criar job diário (cron) para Scheduler Agent:
Varre todos os usuários
Identifica itens devido para revisão
Cria schedule do dia
API endpoints: /dashboard/{user_id}, /schedule/today
Frontend: gráficos interativos (Recharts)
Testar transparência: usuário entende claramente seu progresso
Fase 9: Onboarding & Assessment
Arquivos críticos a criar:

frontend/src/pages/Onboarding.tsx
frontend/src/components/assessment/InitialAssessment.tsx
backend/app/api/v1/endpoints/assessment.py
Tarefas:

Implementar fluxo de onboarding:
Registro de usuário
Configuração de perfil (objetivos, tempo disponível)
Implementar Assessment Inicial:
20 palavras de vocabulário
5 regras de gramática
5 sons básicos
1 minuto de conversação
Lógica de determinação de nível (Iniciante vs Intermediário)
Criar plano personalizado inicial
Frontend: wizard de onboarding passo-a-passo
Testar experiência completa de novo usuário
Fase 10: Níveis (Iniciante vs Intermediário)
Arquivos a modificar:

Todos os agentes (adicionar lógica de nível)
backend/app/data/ - Separar conteúdo por nível
Tarefas:

Iniciante:
Filtrar para 2000 palavras comuns
Sons individuais (fonemas isolados)
Gramática básica
Conversação estruturada
Intermediário:
Vocabulário avançado
Conexão de sons (linking, reduction)
Variedade de sotaques (implementar múltiplas vozes TTS)
Conversação complexa
Implementar transição automática (via Assessment Contínuo)
Testar ambos os níveis end-to-end
Fase 11: Testing & Refinement
Arquivos críticos a criar:

backend/tests/test_agents/
backend/tests/test_api/
backend/tests/conftest.py
Tarefas:

Testes unitários para todos os agentes
Testes de integração para fluxos críticos
Testes de API (endpoints)
Teste de performance:
API response time < 200ms (p95)
WebSocket latency < 100ms
Refinamento de UX/UI
Otimização de custos Azure (caching, rate limiting)
Documentação de API
Fase 12: Deployment
Arquivos críticos a criar:

infrastructure/azure/scripts/deploy.sh
docker-compose.yml - Para desenvolvimento local
backend/Dockerfile
frontend/Dockerfile
Tarefas:

Setup Azure App Service para backend
Setup Azure Static Web Apps para frontend
Configurar CI/CD (GitHub Actions)
Setup monitoring:
Application Insights
Logging centralizado
Setup alertas (erros, latência, custos)
Deploy para produção
Teste de aceitação do usuário
Arquivos Críticos (Ordem de Importância)
Tier 1: Fundação (Bloqueia tudo)
backend/app/config.py - Configurações centralizadas
backend/app/services/azure_openai_service.py - Usado por todos os agentes
backend/app/services/azure_speech_service.py - Crítico para pronúncia/fala
backend/app/services/cosmos_db_service.py - Persistência
backend/app/utils/srs_algorithm.py - SRS é core do sistema
Tier 2: Orquestração (Coordenação)
backend/app/agents/base_agent.py - Interface comum
backend/app/agents/orchestrator.py - LangGraph, coordena tudo
backend/app/agents/scheduler_agent.py - SRS scheduling
Tier 3: Pilares (Funcionalidades)
backend/app/agents/vocabulary_agent.py
backend/app/agents/grammar_agent.py
backend/app/agents/pronunciation_agent.py
backend/app/agents/speaking_agent.py
backend/app/agents/error_integration_agent.py - Integração entre pilares
Tier 4: Frontend (UI)
frontend/src/services/websocket.ts - Comunicação real-time
frontend/src/components/speaking/ConversationInterface.tsx - Integra todos os pilares
Verificação (Como Testar End-to-End)
Teste 1: Fluxo Completo de Novo Usuário
Acessar app → criar conta
Onboarding: preencher perfil
Assessment inicial: completar todas as seções
Verificar nível determinado (Iniciante/Intermediário)
Dashboard: verificar plano personalizado e primeira atividade
Teste 2: Vocabulário com SRS
Acessar pilar Vocabulário
Completar 5 exercícios
Verificar no Cosmos DB: vocabulary_progress atualizado
Verificar next_review calculado corretamente
Avançar tempo (mock) para data de revisão
Verificar que palavra aparece em "Revisões Agendadas"
Completar revisão
Verificar intervalo aumentado (SRS funcionando)
Teste 3: Gramática com Explicação
Acessar pilar Gramática
Estudar regra (ex: Present Perfect)
Ver comparação PT-EN
Escrever explicação com suas palavras
Verificar score de avaliação (GPT-4)
Completar exercícios práticos
Verificar no Cosmos DB: grammar_progress + explicação armazenada
Teste 4: Pronúncia com Feedback
Acessar pilar Pronúncia
Estudar fonema /θ/ (think)
Ver diagrama de boca
Escutar áudio (TTS)
Gravar pronúncia
Verificar feedback detalhado:
Phoneme detectado
Accuracy score
Sugestão específica
Repetir até accuracy > 85%
Verificar progresso armazenado
Teste 5: Conversação com Geração de Atividades
Acessar pilar Fala
Iniciar conversação
Cometer erro gramatical: "I waked up at 7"
Cometer erro de pronúncia: /θ/ → /s/
Continuar conversa (5 turnos)
Finalizar sessão
Verificar atividades geradas:
Nova atividade em Grammar (irregular past tense)
Nova atividade em Pronunciation (fonema /θ/)
Acessar Grammar → verificar atividade "waked → woke"
Acessar Pronunciation → verificar atividade /θ/
Confirmar integração entre pilares
Teste 6: Sistema de Revisão
Não usar palavra específica por 7 dias
Verificar Scheduler Agent identifica
Verificar aparece em "Revisões Agendadas"
Completar revisão
Voltar a usar a palavra em conversação
Verificar last_7_days_usage aumenta
Verificar revisão removida automaticamente
Teste 7: Avaliação Contínua e Mudança de Nível
Completar 15 sessões como Iniciante
Manter accuracy > 85% em todos os pilares
Verificar Assessment Contínuo é acionado
Verificar relatório de progresso
Verificar upgrade: Iniciante → Intermediário
Verificar novo conteúdo desbloqueado:
Conexão de sons
Variedade de sotaques
Conversação avançada
Teste 8: Dashboard e Transparência
Acessar Dashboard
Verificar progresso por pilar (gráficos)
Verificar nível atual claramente exibido
Verificar revisões agendadas para hoje
Completar atividade
Verificar atualização em tempo real
Verificar streak (dias consecutivos)
Teste 9: Performance
Medir tempo de resposta de API:
GET /vocabulary/next-activity < 200ms
POST /speaking/submit-audio < 500ms (inclui STT)
Medir latência WebSocket < 100ms
Verificar caching funcionando (2ª requisição mais rápida)
Teste 10: Custos Azure
Monitorar uso de Azure OpenAI (tokens)
Monitorar uso de Azure Speech (horas)
Monitorar uso de Cosmos DB (RU/s)
Verificar custos dentro do esperado ($350-800/mês para 100 usuários)
Dependências Críticas
Backend (Python)

fastapi==0.109.0
uvicorn[standard]==0.27.0
langgraph==0.0.20
langchain==0.1.0
azure-cosmos==4.5.1
azure-cognitiveservices-speech==1.34.0
openai==1.10.0  # Azure OpenAI
pydantic==2.5.3
websockets==12.0
Frontend (React)

react: ^18.2.0
typescript: ^5.3.3
react-router-dom: ^6.21.1
axios: ^1.6.5
socket.io-client: ^4.6.1
@reduxjs/toolkit: ^2.0.1
recharts: ^2.10.3  # Gráficos
tailwindcss: ^3.4.1
Considerações Importantes
Performance
Caching: Redis para vocabulário comum, regras gramaticais, sons
Partition Key: user_id em todos os containers Cosmos DB
Rate Limiting: Limitar chamadas Azure OpenAI por usuário
Segurança
JWT: Autenticação stateless
HTTPS: Apenas conexões seguras
Audio: NÃO armazenar permanentemente (apenas processar)
GDPR: Permitir exportação/exclusão de dados
Custos Estimados (Azure)
Cosmos DB: $50-100/mês (<1000 usuários)
Azure OpenAI (GPT-4): $200-500/mês
Azure Speech: $100-200/mês
Total: $350-800/mês
Escalabilidade
FastAPI stateless: scale horizontal
WebSocket: Redis pub/sub para multi-instance
Background jobs: Azure Functions ou Celery
Próximos Passos
Após aprovação deste plano, começaremos pela Fase 1 (Setup & Infrastructure), criando:

Estrutura de diretórios completa
Provisionamento de recursos Azure
Configurações básicas de backend e frontend
Schemas Cosmos DB