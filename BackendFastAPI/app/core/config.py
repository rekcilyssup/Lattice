from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    APP_NAME: str = 'lattice-backend-fastapi'
    ENV: str = 'development'
    PORT: int = 8080
    API_BASE_PATH: str = '/api/v1'
    CORS_ORIGIN: str = 'http://localhost:3000'

    POSTGRES_HOST: str = '127.0.0.1'
    POSTGRES_PORT: int = 5433
    POSTGRES_DB: str = 'lattice'
    POSTGRES_USER: str = 'lattice'
    POSTGRES_PASSWORD: str = 'lattice'
    POSTGRES_SSL: bool = False

    UPLOAD_DIR: str = 'storage/uploads'
    MAX_FILE_SIZE_MB: int = 20
    EMBEDDING_DIMENSION: int = 1536

    EMBEDDING_PROVIDER: str = 'ollama'
    EMBEDDING_MODEL: str = 'text-embedding-3-small'
    OLLAMA_BASE_URL: str = 'http://localhost:11434'
    OLLAMA_EMBEDDING_MODEL: str = 'nomic-embed-text'

    LLM_PROVIDER: str = 'ollama'
    LLM_MODEL: str = 'llama3.2:1b'
    LLM_TEMPERATURE: float = 0

    OPENAI_API_KEY: str = ''
    GEMINI_API_KEY: str = ''
    COHERE_API_KEY: str = ''
    RERANK_PROVIDER: str = 'heuristic'
    TOP_K_DENSE: int = 15
    TOP_K_SPARSE: int = 15
    TOP_K_RERANK: int = 8


settings = Settings()
