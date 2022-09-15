from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from src.db import get_db
from src.db.file_system_items import FileSystemItems
from src.helpers.validations import items_have_correct_parent_id_validation, date_validation
from src.schemas.file_system_items import FileSystemItemImport, NodeOut, ItemsOut

file_system_items_router = APIRouter()


@file_system_items_router.post(
    path='/imports',
    description='Importing the new elements or updating existing ones.')
async def import_file_system_items(queue: FileSystemItemImport, db=Depends(get_db)):
    await items_have_correct_parent_id_validation(queue.items)

    await FileSystemItems.insert_items_or_update_existing_ones(db, queue.items, queue.updateDate)
    return {'status': 'ok'}


@file_system_items_router.delete(
    path='/delete/{item_id}',
    description='Deleting file system element by its ID')
async def delete_file_system_items(item_id: str, date: str, db=Depends(get_db)):
    date = await date_validation(date)

    deleted_item = await FileSystemItems.find_item_and_delete(db, item_id, date)
    if not deleted_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Item not found',
        )
    return {'status': 'ok'}


@file_system_items_router.get(
    path='/nodes/{item_id}',
    response_model=NodeOut,
    description='Getting the node part of system files tree.')
async def get_node_of_system_items(item_id: str, db=Depends(get_db)):
    item = await FileSystemItems.find_item_and_retrieve(db, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Item not found',
        )
    return item


@file_system_items_router.get(
    path='/updates',
    response_model=ItemsOut,
    description='Getting a list of files that have been updated in the last 24 hours passed from the request time.',
)
async def get_previously_updated_items(date: str, db=Depends(get_db)):
    date = await date_validation(date)

    updated_items = await FileSystemItems.get_items_updated_for_the_last_24_hours_from_request_date(db, date)
    return {'items': updated_items}


@file_system_items_router.get(
    path='/node/{item_id}/history',
    description='Getting an update story of the element.'
)
async def get_item_update_history(item_id: str, date_start: str = None, date_end: str = None, db=Depends(get_db)):
    date_start = await date_validation(date_start)
    date_end = await date_validation(date_end)

    item_update_history = await FileSystemItems.get_item_update_history(db, item_id, date_start, date_end)
    if item_update_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Item not found',
        )

    return {'items': item_update_history}
