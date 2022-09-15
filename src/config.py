import os

from pydantic import BaseSettings


class Settings(BaseSettings):
    HOST: str = os.getenv('HOST', '127.0.0.1')
    PORT: int = os.getenv('PORT', 80)

    MONGO_DB: str = os.getenv('MONGO_DB', 'enrolment')
    MONGODB_CONNECTION_URL: str = 'mongodb://test:test@localhost:27017'

    CELERY_BROKER_URL: str = 'redis://redis:6379'

    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379')

    class Config:
        case_sensitive = True


settings = Settings()
