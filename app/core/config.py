# Pydantic Settings
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Define variables and their types (automatic validation)
    # entries from .env
    PROJECT_NAME: str
    DEBUG: bool = False
    LOGURU_LEVEL: str
    GROQ_MODEL: str
    DB_NAME: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    ADMIN_SECRET_KEY: str
    # add more entries from .env

    # entries harcoded
    SHOW_SQL: bool = False

    # Setup to read the .env file
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # Ignore extra .env variables not listed here
    )

# Instantiate for global app use
settings = Settings()
