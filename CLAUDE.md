# CLAUDE.md - English Teacher Multi-Agents

## Visão Geral do Projeto

Plataforma web para ensino de inglês americano utilizando um sistema de **9 agentes de IA especializados** orquestrados via LangGraph. O foco é no aprendizado científico e personalizado através de 4 pilares: Vocabulário, Gramática, Pronúncia e Conversação.

## Stack Tecnológico

### Backend
- **Python 3.11+** com **FastAPI**
- **LangGraph** para orquestração multi-agentes
- **Azure OpenAI** (GPT-4) para geração de conteúdo
- **Azure Speech Services** para reconhecimento e síntese de voz
- **Azure Cosmos DB** para persistência
- **Pydantic** para validação de dados
- **Socket.io** para comunicação em tempo real

### Frontend
- **React 18+** com **TypeScript**
- **Vite** como bundler
- **TailwindCSS** + **DaisyUI** para estilização
- **Redux Toolkit** para gerenciamento de estado
- **Socket.io Client** para WebSocket
- **React Mic** + **WaveSurfer.js** para áudio

## Arquitetura de Agentes

O sistema possui 9 agentes especializados que se comunicam via LangGraph:

| Agente | Responsabilidade |
|--------|------------------|
| `Orchestrator` | Coordena todos os agentes e fluxos de aprendizado |
| `Assessment` | Avaliação inicial e contínua do aluno |
| `Vocabulary` | Ensino das 2000 palavras + vocabulário técnico com SRS |
| `Grammar` | Gramática ativa com comparação PT-EN |
| `Pronunciation` | Validação de pronúncia via Azure Speech (shadowing) |
| `Speaking` | Conversação em tempo real com correção automática |
| `Scheduler` | Agendamento de revisões (algoritmo SM-2) |
| `ErrorIntegration` | Detecção de erros e geração de atividades corretivas |
| `Progress` | Métricas e acompanhamento de progresso |

## Estrutura do Projeto

```
/backend/
├── app/
│   ├── main.py              # Entry point FastAPI
│   ├── config.py            # Configurações (Pydantic Settings)
│   ├── agents/              # Implementação dos 9 agentes
│   ├── services/            # Integrações Azure
│   ├── models/              # Modelos Pydantic
│   ├── schemas/             # Schemas de request/response
│   ├── api/v1/endpoints/    # Endpoints REST
│   ├── core/                # Segurança, WebSocket, auth
│   └── utils/               # Algoritmo SRS, utilitários
└── requirements.txt

/frontend/
├── src/
│   ├── components/          # Componentes React por pilar
│   ├── pages/               # Páginas principais
│   ├── services/            # API, WebSocket, áudio
│   ├── store/               # Redux slices
│   └── hooks/               # Custom hooks
└── package.json
```

## Comandos Essenciais

### Backend
```bash
# Instalar dependências
cd backend && pip install -r requirements.txt

# Rodar servidor de desenvolvimento
uvicorn app.main:app --reload --port 8000

# Rodar testes
pytest -v --cov=app

# Verificar tipos
mypy app/
```

### Frontend
```bash
# Instalar dependências
cd frontend && npm install

# Rodar servidor de desenvolvimento
npm run dev

# Build para produção
npm run build

# Linting
npm run lint
```

## Convenções de Código

### Python (Backend)
- **PEP 8** com line length de 100 caracteres
- **Type hints** obrigatórios em todas as funções públicas
- **Docstrings** no formato Google para classes e funções complexas
- **async/await** para operações I/O (Azure, DB, WebSocket)
- Nomenclatura:
  - Classes: `PascalCase`
  - Funções/variáveis: `snake_case`
  - Constantes: `UPPER_SNAKE_CASE`

### TypeScript (Frontend)
- **ESLint** + **Prettier** para formatação
- **Interfaces** preferidas sobre types para objetos
- **Functional components** com hooks
- Nomenclatura:
  - Componentes: `PascalCase`
  - Funções/hooks: `camelCase`
  - Constantes: `UPPER_SNAKE_CASE`

### Agentes (LangGraph)
- Cada agente deve herdar da classe base em `agents/base.py`
- Estado compartilhado via `TypedDict` em `agents/state.py`
- Comunicação entre agentes apenas via canais definidos no grafo
- Logging estruturado para debug do fluxo de agentes

## Padrões de Implementação

### Criando um Novo Agente
```python
# backend/app/agents/novo_agent.py
from typing import TypedDict
from langgraph.graph import StateGraph

class NovoAgentState(TypedDict):
    input: str
    output: str
    # ... outros campos

class NovoAgent:
    def __init__(self, config: Settings):
        self.config = config
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        # Implementar grafo do agente
        pass

    async def process(self, state: NovoAgentState) -> NovoAgentState:
        # Lógica principal do agente
        pass
```

### Endpoints REST
```python
# backend/app/api/v1/endpoints/novo_endpoint.py
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.novo import NovoRequest, NovoResponse

router = APIRouter()

@router.post("/", response_model=NovoResponse)
async def criar_novo(request: NovoRequest):
    # Implementação
    pass
```

### Componentes React
```typescript
// frontend/src/components/NomeComponente/NomeComponente.tsx
import { FC } from 'react';

interface NomeComponenteProps {
  // props tipadas
}

export const NomeComponente: FC<NomeComponenteProps> = ({ ...props }) => {
  return (
    // JSX
  );
};
```

## Variáveis de Ambiente

Copiar `.env.example` para `.env` e configurar:

### Obrigatórias
- `AZURE_OPENAI_API_KEY` - Chave da API Azure OpenAI
- `AZURE_OPENAI_ENDPOINT` - Endpoint do serviço
- `AZURE_SPEECH_KEY` - Chave do Azure Speech Services
- `AZURE_SPEECH_REGION` - Região (ex: eastus)
- `COSMOS_DB_ENDPOINT` - Endpoint do Cosmos DB
- `COSMOS_DB_KEY` - Chave primária do Cosmos DB
- `JWT_SECRET_KEY` - Chave para tokens JWT

### Opcionais
- `REDIS_URL` - URL do Redis para cache (produção)
- `LOG_LEVEL` - Nível de log (default: INFO)

## Algoritmo SRS (SM-2)

O sistema usa Spaced Repetition para otimizar memorização:

```
intervalo_inicial = 1 dia
segundo_intervalo = 6 dias
próximo_intervalo = intervalo_anterior × ease_factor

ease_factor ajustado por performance:
- Resposta perfeita (5): +0.1
- Resposta boa (4): +0.05
- Resposta ok (3): 0
- Resposta ruim (2): -0.15
- Resposta péssima (1): -0.3
```

## Targets de Performance

- API REST: < 200ms (p95)
- WebSocket: < 100ms latência
- Azure Speech: < 500ms resposta
- Frontend: LCP < 2.5s, FID < 100ms

## Testes

### Backend
- Usar `pytest` com fixtures assíncronas
- Mockar serviços Azure com `unittest.mock`
- Coverage mínimo: 80%

### Frontend
- Usar `vitest` + `@testing-library/react`
- Testar hooks customizados isoladamente
- Testar integração Redux com store mockada

## Dicas para o Claude

1. **Ao implementar agentes**: Sempre verificar se o estado compartilhado (`AgentState`) possui todos os campos necessários antes de adicionar novos
2. **Azure Services**: Todos os clientes Azure devem ser inicializados de forma lazy no `main.py`
3. **WebSocket**: Usar namespaces separados para cada tipo de comunicação (assessment, speaking, etc.)
4. **Erros**: Usar `HTTPException` com códigos apropriados e mensagens em português para o usuário
5. **Tipos**: O projeto usa Pydantic v2 - usar `model_validate()` em vez de `parse_obj()`

## Links Úteis

- [LangGraph Docs](https://python.langchain.com/docs/langgraph)
- [Azure Speech SDK](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
