from datetime import datetime


async def process_folders_graph(folders_graph, node_folder_id, upside=False):
    folder_ids = []
    parent_ids = []

    for folder_data in folders_graph:
        folder_ids.append(folder_data[0])
        parent_ids.append(folder_data[1])

    linked_folder_ids = []
    stack = [node_folder_id]

    if upside:
        while len(stack) != 0:
            for i, folder_id in enumerate(folder_ids):
                linked_folder_id = stack[0]
                if folder_id == linked_folder_id:
                    linked_folder_ids.append(stack.pop())
                    if parent_ids[i]:
                        stack.append(parent_ids[i])
                    break

    while len(stack) != 0:
        for folder_id in stack:
            lower_level_nodes = [folder_ids[i] for i, node_id in enumerate(parent_ids) if node_id == folder_id]
            stack = lower_level_nodes + stack
            if stack:
                linked_folder_ids.append(stack.pop())

    return linked_folder_ids, [folder_data for folder_data in folders_graph if folder_data not in linked_folder_ids]


async def process_node_to_retrieve(node_to_retrieve_id, unordered_node_elements):
    files = []
    folders = []
    for node in unordered_node_elements:
        if node['type'] == 'FILE':
            node['children'] = None
            files.append(node)
        else:
            node['children'] = []
            folders.append(node)
        node['date'] = datetime.isoformat(node['date']) + 'Z'

    for file in files:
        for folder in folders:
            if file['parentId'] == folder['id']:
                folder['children'].append(file)
                continue

    for child in folders:
        for parent in folders:
            if child['parentId'] == parent['id']:
                parent['children'].append(child)

    return [folder for folder in folders if folder['id'] == node_to_retrieve_id][0]
