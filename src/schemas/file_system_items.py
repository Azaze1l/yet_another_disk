from datetime import datetime
from typing import Optional, List

from fastapi import HTTPException
from pydantic import BaseModel, validator, Field
from starlette import status


class Item(BaseModel):
    id: str = Field(..., title='Id of file system item')
    url: Optional[str] = Field(None, max_length=255, title='URL of file system item')
    parentId: Optional[str] = Field(None, title='Parent ID of file system item')
    size: Optional[int] = Field(None, gt=0, title='Size of file system item')
    type: str = Field(..., title='Type of file system item')
    date: Optional[str] = Field(None)
    update_history: Optional[List] = Field([])

    # TODO валидация на не None size у файла
    @validator('type')
    def type_match(cls, item_type):
        if item_type in ('FOLDER', 'FILE'):
            return item_type

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Item type must be FOLDER or FILE',
        )


class FileSystemItemImport(BaseModel):
    items: List[Item] = Field(..., title='List of file system items to import')
    updateDate: str = Field(..., title='Update date of imported file system items')

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "элемент_1_4",
                        "url": "/file/url1",
                        "parentId": "элемент_1_1",
                        "size": 234,
                        "type": "FILE",
                    },
                ],
                "updateDate": "2022-05-28T21:12:01.000Z",
            },
        }

    @validator('updateDate')
    def update_date_validation(cls, update_date_string):
        try:
            processed_date = update_date_string
            if not processed_date[-1].isdigit():
                processed_date = update_date_string[:-1]

            return datetime.fromisoformat(processed_date)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=e.args[0],
            )

    @validator('items')
    def import_items_validation(cls, items_list):
        for item in items_list:
            if item.type == 'FOLDER':
                if item.url is not None or item.size is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='Folder must have url=Null and size=Null while import',
                    )
            else:
                if item.url is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='File must have a url while import',
                    )

        items_id_list = [item.id for item in items_list]
        if len(items_id_list) != len(set(items_id_list)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Items must have unique ids\' while import',
            )

        return items_list


class NodeOut(BaseModel):
    id: str = Field(..., title='Id of file system item')
    url: Optional[str] = Field(..., title='URL of file system item')
    parentId: Optional[str] = Field(..., title='Parent ID of file system item')
    size: Optional[int] = Field(..., title='Size of file system item')
    type: str = Field(..., title='Type of file system item')
    date: str = Field(..., title='Date of the last item update')
    children: Optional[List] = Field(None, title='Child elements of the lower levels of the node')

    class Config:
        schema_extra = {
            "example": {
                "id": "элемент_1_2",
                "url": None,
                "type": "FOLDER",
                "parentId": None,
                "date": "2022-05-28T21:12:01.000Z",
                "size": 12,
                "children": [
                    {
                        "url": "/file/url1",
                        "id": "элемент_1_3",
                        "size": 4,
                        "date": "2022-05-28T21:12:01.000Z",
                        "type": "FILE",
                        "parentId": "элемент_1_2"
                    },
                    {
                        "type": "FOLDER",
                        "url": None,
                        "id": "элемент_1_1",
                        "date": "2022-05-26T21:12:01.000Z",
                        "parentId": "элемент_1_2",
                        "size": 8,
                        "children": [
                            {
                                "url": "/file/url2",
                                "id": "элемент_1_4",
                                "parentId": "элемент_1_1",
                                "date": "2022-05-26T21:12:01.000Z",
                                "size": 8,
                                "type": "FILE"
                            },
                        ],
                    },
                ],
            },
        }


class ItemsOut(BaseModel):
    items: List[Item] = Field(..., title='List of file system elements')

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "элемент_1_4",
                        "url": "/file/url1",
                        "date": "2022-05-28T21:12:01.000Z",
                        "parentId": "элемент_1_1",
                        "size": 234,
                        "type": "FILE",
                    },
                ],
            },
        }
