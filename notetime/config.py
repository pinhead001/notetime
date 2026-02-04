import os


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./notetime.db")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")


settings = Settings()
