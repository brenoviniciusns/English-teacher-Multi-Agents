"""
Configuration settings for the English Learning App.
All environment variables and app settings are centralized here.
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "English Learning Multi-Agent App"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_MAX_TOKENS: int = 1000
    AZURE_OPENAI_TEMPERATURE: float = 0.7

    # Azure Speech Services
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str
    AZURE_SPEECH_LANGUAGE: str = "en-US"
    # Vozes disponíveis para TTS
    AZURE_SPEECH_VOICE_AMERICAN: str = "en-US-JennyNeural"  # Feminina americana
    AZURE_SPEECH_VOICE_AMERICAN_MALE: str = "en-US-GuyNeural"  # Masculina americana
    AZURE_SPEECH_VOICE_BRITISH: str = "en-GB-SoniaNeural"  # Feminina britânica
    AZURE_SPEECH_VOICE_BRITISH_MALE: str = "en-GB-RyanNeural"  # Masculina britânica

    # Azure Cosmos DB
    COSMOS_DB_ENDPOINT: str
    COSMOS_DB_KEY: str
    COSMOS_DB_DATABASE_NAME: str = "english_learning_db"
    # Container names
    COSMOS_DB_USERS_CONTAINER: str = "users"
    COSMOS_DB_VOCABULARY_PROGRESS_CONTAINER: str = "vocabulary_progress"
    COSMOS_DB_GRAMMAR_PROGRESS_CONTAINER: str = "grammar_progress"
    COSMOS_DB_PRONUNCIATION_PROGRESS_CONTAINER: str = "pronunciation_progress"
    COSMOS_DB_ACTIVITIES_CONTAINER: str = "activities"
    COSMOS_DB_SPEAKING_SESSIONS_CONTAINER: str = "speaking_sessions"
    COSMOS_DB_SCHEDULE_CONTAINER: str = "schedule"

    # Redis Cache (opcional para produção)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    USE_REDIS: bool = False  # Ativar em produção

    # JWT Authentication
    SECRET_KEY: str  # Gerar com: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas

    # SRS (Spaced Repetition System) Settings
    SRS_INITIAL_INTERVAL_DAYS: int = 1
    SRS_SECOND_INTERVAL_DAYS: int = 6
    SRS_INITIAL_EASE_FACTOR: float = 2.5
    SRS_MIN_EASE_FACTOR: float = 1.3
    SRS_LOW_FREQUENCY_THRESHOLD_DAYS: int = 7
    SRS_LOW_ACCURACY_THRESHOLD: int = 80

    # Learning Levels
    BEGINNER_VOCABULARY_LIMIT: int = 2000  # 2000 palavras mais comuns
    BEGINNER_PRONUNCIATION_ACCURACY_TARGET: int = 85
    INTERMEDIATE_UPGRADE_THRESHOLD: int = 85  # % accuracy média

    # Assessment Settings
    INITIAL_ASSESSMENT_VOCABULARY_COUNT: int = 20
    INITIAL_ASSESSMENT_GRAMMAR_COUNT: int = 5
    INITIAL_ASSESSMENT_PRONUNCIATION_COUNT: int = 5
    CONTINUOUS_ASSESSMENT_FREQUENCY: int = 5  # A cada 5 sessões

    # Speaking/Conversation Settings
    SPEAKING_SESSION_MIN_TURNS: int = 5
    SPEAKING_SESSION_MAX_TURNS: int = 10
    SPEAKING_TOPICS: list[str] = [
        "daily_routine",
        "work",
        "technology",
        "data_engineering",
        "artificial_intelligence",
        "hobbies",
        "travel"
    ]

    # WebSocket Settings
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # segundos
    WEBSOCKET_TIMEOUT: int = 300  # 5 minutos

    # File Upload Settings
    MAX_AUDIO_FILE_SIZE_MB: int = 10
    ALLOWED_AUDIO_FORMATS: list[str] = ["wav", "mp3", "webm", "ogg"]

    # Rate Limiting (requests per minute)
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_OPENAI_PER_HOUR: int = 100  # Limitar custos

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()


# Singleton instance
settings = get_settings()
