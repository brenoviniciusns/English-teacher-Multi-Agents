"""
Base Agent
Abstract base class for all agents in the multi-agent system.
Provides common interface, logging, and service access.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
from datetime import datetime

from app.config import Settings, get_settings
from app.services.azure_openai_service import AzureOpenAIService, azure_openai_service
from app.services.azure_speech_service import AzureSpeechService, azure_speech_service
from app.services.cosmos_db_service import CosmosDBService, cosmos_db_service


# Type variable for agent state
StateT = TypeVar("StateT")


class BaseAgent(ABC, Generic[StateT]):
    """
    Abstract base class for all agents.

    Each agent should:
    - Handle a specific domain (vocabulary, grammar, etc.)
    - Have access to Azure services
    - Log its operations for debugging
    - Return updates to the shared state
    """

    def __init__(
        self,
        settings: Settings | None = None,
        openai_service: AzureOpenAIService | None = None,
        speech_service: AzureSpeechService | None = None,
        db_service: CosmosDBService | None = None
    ):
        """
        Initialize base agent with services.

        Args:
            settings: Application settings (uses singleton if not provided)
            openai_service: Azure OpenAI service (uses singleton if not provided)
            speech_service: Azure Speech service (uses singleton if not provided)
            db_service: Cosmos DB service (uses singleton if not provided)
        """
        self.settings = settings or get_settings()
        self.openai_service = openai_service or azure_openai_service
        self.speech_service = speech_service or azure_speech_service
        self.db_service = db_service or cosmos_db_service

        # Setup logging for this agent
        self.logger = logging.getLogger(f"agent.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging and identification"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description for documentation"""
        pass

    @abstractmethod
    async def process(self, state: StateT) -> StateT:
        """
        Process the current state and return updated state.

        This is the main entry point for agent logic.

        Args:
            state: Current shared state

        Returns:
            Updated state with agent's modifications
        """
        pass

    def log_start(self, context: dict | None = None) -> None:
        """Log agent starting to process"""
        msg = f"[{self.name}] Starting processing"
        if context:
            msg += f" - Context: {context}"
        self.logger.info(msg)

    def log_complete(self, result: Any = None) -> None:
        """Log agent completed processing"""
        msg = f"[{self.name}] Processing complete"
        if result:
            msg += f" - Result: {result}"
        self.logger.info(msg)

    def log_error(self, error: Exception, context: dict | None = None) -> None:
        """Log agent error"""
        msg = f"[{self.name}] Error: {str(error)}"
        if context:
            msg += f" - Context: {context}"
        self.logger.error(msg, exc_info=True)

    def log_debug(self, message: str, data: Any = None) -> None:
        """Log debug information"""
        msg = f"[{self.name}] {message}"
        if data:
            msg += f" - Data: {data}"
        self.logger.debug(msg)


class AgentResult:
    """
    Standard result object returned by agents.
    Used for consistent error handling and result passing.
    """

    def __init__(
        self,
        success: bool,
        data: dict | None = None,
        error: str | None = None,
        agent_name: str | None = None
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.agent_name = agent_name
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert result to dictionary"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def success_result(cls, data: dict, agent_name: str) -> "AgentResult":
        """Create a success result"""
        return cls(success=True, data=data, agent_name=agent_name)

    @classmethod
    def error_result(cls, error: str, agent_name: str) -> "AgentResult":
        """Create an error result"""
        return cls(success=False, error=error, agent_name=agent_name)


class AgentContext:
    """
    Context object passed to agents for current request.
    Contains user info, session data, and request-specific details.
    """

    def __init__(
        self,
        user_id: str,
        session_id: str | None = None,
        request_type: str | None = None,
        pillar: str | None = None,
        metadata: dict | None = None
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.request_type = request_type
        self.pillar = pillar
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert context to dictionary"""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_type": self.request_type,
            "pillar": self.pillar,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
