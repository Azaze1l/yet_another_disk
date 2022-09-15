import json
import logging

from celery import Celery
from celery.schedules import crontab
from pymongo import MongoClient, ReadPreference
from pymongo.read_concern import ReadConcern
from redis import Redis

from src.config import settings
from src.db.file_system_items import collection as fs_items_collection_name

logger = logging.getLogger("tasks")

celery_app = Celery("worker", broker=settings.CELERY_BROKER_URL)
logger.info('TEST')


@celery_app.task
def sync_folder_ids_list_task():
    def insert_folder_ids_in_cash():
        fs_items_collection = session.client[settings.MONGO_DB][fs_items_collection_name]
        cursor = fs_items_collection.find({'type': 'FOLDER'})
        folder_objects = list(cursor)

        folder_graph = [[obj['id'], obj['parentId']] for obj in folder_objects]
        redis = Redis().from_url(settings.REDIS_URL)
        redis.set('folders_graph', json.dumps(folder_graph))
        logger.info(f'Folder graph has been synced.\n Data{folder_graph}')

    client = MongoClient(
        settings.MONGODB_CONNECTION_URL,
        serverSelectionTimeoutMS=10,
    )

    logger.info("sync_folder_ids_list_task: STARTED")
    with client.start_session() as session:
        session.with_transaction(
            lambda s: insert_folder_ids_in_cash(),
            read_concern=ReadConcern("local"),
            read_preference=ReadPreference.PRIMARY,
        )
    logger.info("sync_folder_ids_list_task: FINISHED")


celery_app.conf.beat_schedule = {
    "sync_folder_ids_list_task": {
        "task": "src.celery_app.sync_folder_ids_list_task",
        "schedule": crontab(minute=0, hour=0),
    },
}
