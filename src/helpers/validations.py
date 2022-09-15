from datetime import datetime

from fastapi import HTTPException
from starlette import status

from src.cache import cache


async def items_have_correct_parent_id_validation(items_list):
    """
    Check if item's parent id is folder
    """
    current_folders_graph = await cache.get('folders_graph')
    if current_folders_graph is None:
        current_folders_graph = []

    for folder in [[folder.id, folder.parentId] for folder in items_list if folder.type == 'FOLDER']:
        if folder not in current_folders_graph:
            current_folders_graph.append(folder)

    folder_ids = set(folder[0] for folder in current_folders_graph)
    parent_ids = set(item.parentId for item in items_list if item.parentId is not None)

    if not parent_ids.issubset(folder_ids) and len(folder_ids) != 0 and len(parent_ids) != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='ParentId must be ID of FOLDER type item',
        )
    # update folders graph with new imported data
    await cache.set('folders_graph', current_folders_graph)


async def date_validation(date: str):
    try:
        processed_date = date
        if not processed_date[-1].isdigit():
            processed_date = date[:-1]

        return datetime.fromisoformat(processed_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Date validation failed',
        )
    except TypeError:
        return None
