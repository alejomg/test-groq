# Pydantic Settings

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Define variables and their types (automatic validation)
    PROJECT_NAME: str
    DEBUG: bool = False
    GROQ_MODEL: str
    #add more entries from .env

    # Setup to read the .env file
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # Ignore extra .env variables not listed here
    )

# Instantiate for global app use
settings = Settings()
