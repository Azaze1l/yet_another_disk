import logging.config

import uvicorn
from fastapi import FastAPI

from db import connect_to_mongodb, close_mongodb_connection
from src.api import api_router
from src.cache import connect_cache, disconnect_cache
from src.config import settings

log_conf = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(process)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "level": "DEBUG",
        }
    },
    "root": {"handlers": ["console"], "level": "DEBUG"},
    "loggers": {
        "gunicorn": {"propagate": True},
        "uvicorn": {"propagate": True},
        "uvicorn.access": {"propagate": True},
        "events": {"propagate": True},
        "tasks": {"propagate": True},
    },
}
logging.config.dictConfig(log_conf)

app = FastAPI(
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.on_event('startup')
async def startup_event():
    await connect_to_mongodb()
    await connect_cache()


@app.on_event('shutdown')
async def shutdown_event():
    await close_mongodb_connection()
    await disconnect_cache()

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=int(settings.PORT))
