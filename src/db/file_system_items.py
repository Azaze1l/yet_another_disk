from datetime import datetime, timedelta
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.cache import cache
from src.helpers.processing import process_folders_graph, process_node_to_retrieve

collection = 'file_system_items'


class FileSystemItems:

    @staticmethod
    async def insert_items_or_update_existing_ones(db: AsyncIOMotorDatabase, items, update_date):
        def _item_is_not_new(item_id, prev_items):
            for item in prev_items:
                if item['id'] == item_id:
                    return item

        def _item_is_deprived(new_inst_parent_id, prev_inst_parent_id):
            return new_inst_parent_id != prev_inst_parent_id

        def _item_size_change(new_inst_size, prev_inst_size):
            return new_inst_size - prev_inst_size

        def _item_still_the_same(new_inst, prev_inst):
            return all(
                [new_inst.id == prev_inst['id'], new_inst.url == prev_inst['url'], new_inst.size == prev_inst['size'],
                 new_inst.parentId == prev_inst['parentId'], new_inst.type == prev_inst['type']])

        def _item_url_change(new_inst_url, prev_inst_url):
            return new_inst_url == prev_inst_url

        def _update_history(prev_inst_of_items, processed_items):
            for processed_item in processed_items:
                prev_inst = prev_inst_of_items.get(processed_item['id'])
                if prev_inst:
                    processed_item['update_history'].append({
                        'url': prev_inst['url'],
                        'size': prev_inst['size'],
                        'parentId': prev_inst['parentId'],
                        'type': prev_inst['type'],
                        'date': prev_inst['date'],
                    })
            return processed_items

        def _change_size(prev_inst, size_inc):
            return {
                'id': prev_inst['id'],
                'url': prev_inst['url'],
                'size': prev_inst['size'] + size_inc,
                'parentId': prev_inst['parentId'],
                'type': prev_inst['type'],
                'date': update_date,
                'update_history': prev_inst['update_history']
            }

        """
        OPTIONS
        
        1) NEW_ITEM: increase size of upper lvl folders of the new item (if new_item_id not in prev_item_ids)
        2) ITEM_SIZE_CHANGE: increase size of upper lvl folders of the changed item (if prev_instance_item_size != new_instance_item_size)
        3) ITEM_DEPRIVATION: decrease size of upper lvl folders of the changed item (if prev_instance_item_id != new_instance_item_id)
        4) ITEM_URL_CHANGE
        """
        linked_folders_ids = {k: [] for k in [item.id for item in items]}

        folders_graph = await cache.get('folders_graph')
        updated_item_ids = set(item.id for item in items)
        for item in items:
            item.date = update_date
            if item.size is None:
                item.size = 0
            if item.parentId is not None:
                linked_folders, _ = await process_folders_graph(folders_graph, item.parentId, upside=True)
                updated_item_ids.update(linked_folders)
                linked_folders_ids[item.id] = linked_folders

        cursor = db[collection].find({'id': {'$in': list(updated_item_ids)}})
        previous_instance_of_items = await cursor.to_list(None)
        previous_instance_of_items = {v['id']: v for v in previous_instance_of_items}
        await db[collection].delete_many({'id': {'$in': list(updated_item_ids)}})

        processed_items_to_insert = {v: None for v in updated_item_ids}
        new_items = []
        for item in items:
            prev_item = _item_is_not_new(item.id, previous_instance_of_items.values())
            if not prev_item:
                new_items.append(item)
            else:
                item.update_history = prev_item['update_history']

                if _item_is_deprived(item.parentId, prev_item['parentId']):
                    new_branch_to_process = linked_folders_ids[item.id]
                    old_branch_to_process = []
                    if prev_item['parentId'] is not None:
                        old_branch_to_process, _ = await process_folders_graph(folders_graph, prev_item['parentId'],
                                                                               upside=True)
                    for folder_id in old_branch_to_process:
                        prev_item = previous_instance_of_items.get(folder_id)
                        current_item_state = processed_items_to_insert.get(folder_id)
                        if current_item_state:
                            processed_items_to_insert[folder_id] = _change_size(current_item_state, -prev_item['size'])
                            continue
                        if prev_item:
                            processed_items_to_insert[folder_id] = _change_size(prev_item, -prev_item['size'])

                    for folder_id in new_branch_to_process:
                        prev_item = previous_instance_of_items.get(folder_id)
                        current_item_state = processed_items_to_insert.get(folder_id)
                        if current_item_state:
                            processed_items_to_insert[folder_id] = _change_size(current_item_state, item.size)
                            continue
                        if prev_item:
                            processed_items_to_insert[folder_id] = _change_size(prev_item, item.size)

                    if item.type == 'FOLDER':
                        item.size = prev_item['size']

                    processed_items_to_insert[item.id] = item.dict()

                elif _item_size_change(item.size, prev_item['size']) and item.type == 'FILE':
                    branch_to_process = linked_folders_ids[item.id]

                    for folder_id in branch_to_process:
                        prev_item = previous_instance_of_items.get(folder_id)
                        current_item_state = processed_items_to_insert.get(folder_id)
                        if current_item_state:
                            processed_items_to_insert[folder_id] = _change_size(current_item_state,
                                                                                item.size - prev_item['size'])
                            continue
                        if prev_item:
                            processed_items_to_insert[folder_id] = _change_size(prev_item,
                                                                                item.size - prev_item['size'])

                    processed_items_to_insert[item.id] = item.dict()

                elif _item_url_change(item, prev_item):
                    current_item_state = processed_items_to_insert.get(item.id)
                    if current_item_state:
                        current_item_state['url'] = item.url
                    else:
                        processed_items_to_insert[item.id] = item.dict()

                elif _item_still_the_same(item, prev_item):
                    processed_items_to_insert[item.id] = item.dict()

        for item in sorted(new_items, key=lambda v: v.type == 'FOLDER'):
            if item.type == 'FILE':
                branch_to_process = linked_folders_ids[item.id]

                for folder_id in branch_to_process:
                    prev_item = previous_instance_of_items.get(folder_id)
                    current_item_state = processed_items_to_insert.get(folder_id)
                    if current_item_state:
                        processed_items_to_insert[folder_id] = _change_size(current_item_state, item.size)
                        continue
                    if prev_item:
                        processed_items_to_insert[folder_id] = _change_size(prev_item, item.size)
                    else:
                        new_folder = [new_item for new_item in new_items if new_item.id == folder_id][0]
                        processed_items_to_insert[folder_id] = _change_size(new_folder.dict(), size_inc=item.size)

            if not processed_items_to_insert[item.id]:
                processed_items_to_insert[item.id] = item.dict()

        await db[collection].insert_many(
            _update_history(previous_instance_of_items, processed_items_to_insert.values()))

    @staticmethod
    async def find_item_and_delete(db: AsyncIOMotorDatabase, item_id, date: datetime):
        item = await db[collection].find_one_and_delete(filter={'id': item_id})
        if item is None:
            return

        folders_graph = await cache.get('folders_graph')

        if item['parentId'] is not None:
            await FileSystemItems._decrease_linked_folders_size_due_to_file_deprivation(db, folders_graph, item, date)

        if item['type'] == 'FOLDER':
            linked_folders, updated_folders_graph = await process_folders_graph(folders_graph, item_id)
            await db[collection].delete_many(
                filter={
                    '$or': [
                        {'id': {'$in': linked_folders}},
                        {'parentId': {'$in': linked_folders}},
                    ],
                },
            )

            # update folders graph with deleted data
            await cache.set('folders_graph', updated_folders_graph)
        return item

    @staticmethod
    async def _decrease_linked_folders_size_due_to_file_deprivation(db, folders_graph, item, update_date):
        linked_folders, _ = await process_folders_graph(folders_graph, item['parentId'], upside=True)
        cursor = db[collection].find({'id': {'$in': list(linked_folders)}})
        previous_instance_of_items = await cursor.to_list(None)

        await db[collection].delete_many({'id': {'$in': list(linked_folders)}})

        for prev_item in previous_instance_of_items:
            prev_item['update_history'].append(
                {
                    'url': prev_item['url'],
                    'size': prev_item['size'],
                    'parentId': prev_item['parentId'],
                    'type': prev_item['type'],
                    'date': prev_item['date'],
                }
            )
            prev_item['size'] -= item['size']
            prev_item['date'] = update_date

        await db[collection].insert_many(previous_instance_of_items)

    @staticmethod
    async def find_item_and_retrieve(db: AsyncIOMotorDatabase, item_id):
        item = await db[collection].find_one({'id': item_id}, {'_id': False, 'update_history': False})
        if item is None:
            return

        if item['type'] == 'FOLDER':
            folders_graph = await cache.get('folders_graph')
            linked_folders, _ = await process_folders_graph(folders_graph, item_id)
            cursor = db[collection].find(
                {
                    '$or': [
                        {'id': {'$in': linked_folders}},
                        {'parentId': {'$in': linked_folders}},
                    ],
                },
                {'_id': False, 'update_history': False},
            )
            unordered_node_file_system_items = await cursor.to_list(None)

            return await process_node_to_retrieve(item_id, unordered_node_file_system_items)

        return item

    @staticmethod
    async def get_items_updated_for_the_last_24_hours_from_request_date(db: AsyncIOMotorDatabase, date: datetime):
        cursor = db[collection].find({'date': {'$gte': date - timedelta(hours=24), '$lte': date}}, {'_id': False})

        items = await cursor.to_list(None)
        for item in items:
            item['date'] = datetime.isoformat(item['date']) + 'Z'
        return items

    @staticmethod
    async def get_item_update_history(
            db: AsyncIOMotorDatabase,
            item_id: str,
            start_time: Optional[datetime],
            end_time: Optional[datetime],
    ):
        item = await db[collection].find_one({'id': item_id}, {'_id': False})
        if item is None:
            return

        update_history = item['update_history']
        if start_time is None and end_time is None:
            for history_element in update_history:
                history_element.update({'id': item_id})
            return update_history

        history_elements_to_retrieve = []

        for history_element in item['update_history']:
            history_element_to_retrieve = {
                'id': item_id,
                'url': history_element['url'],
                'date': history_element['date'],
                'parentId': history_element['parentId'],
                'size': history_element['size'],
                'type': history_element['type'],
            }
            history_element.update({'id': item_id})
            if start_time is not None and end_time is not None and start_time <= history_element['date'] <= end_time:
                history_elements_to_retrieve.append(history_element_to_retrieve)

            elif start_time is not None and start_time <= history_element['date']:
                history_elements_to_retrieve.append(history_element_to_retrieve)

            elif end_time is not None and end_time >= history_element['date']:
                history_elements_to_retrieve.append(history_element_to_retrieve)
        return history_elements_to_retrieve
