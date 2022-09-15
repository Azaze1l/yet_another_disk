from fastapi import APIRouter

from src.api.file_system_items import file_system_items_router

api_router = APIRouter()

api_router.include_router(file_system_items_router, tags=["Yet Another Disk Open API"])
