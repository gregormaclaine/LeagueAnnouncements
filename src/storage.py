import json
import traceback
from os import path, remove
from typing import Any, List, TypedDict
from logs import log
from config import get_config
from datetime import datetime, timedelta
from uuid import uuid4

FILENAME = 'memory.json'

FILES_PATH = get_config().FILES_PATH
memory_path = path.join(FILES_PATH, FILENAME)


class MemoryEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


class TrackPlayer(TypedDict):
    puuid: str
    name: str
    tag: str
    level: int
    claimed_users: set[int]


class AllottedFile(TypedDict):
    name: str
    path: str
    expiry: datetime


write_memory = {}
allotted_files: List[AllottedFile] = []


def read() -> tuple[dict[int, List[TrackPlayer]], dict[int, int]]:
    global allotted_files
    try:
        with open(memory_path, 'r') as f:
            try:
                memory = json.load(f)
            except json.decoder.JSONDecodeError:
                log('Failed to decode persistent memory',
                    source='main.storage')
                return ({}, {})

            try:
                data = extract_from_data(memory)
                write_memory['tracked_players'] = data[0]
                write_memory['output_channels'] = data[1]
                allotted_files = data[2]
                log('Successfully loaded persistent memory',
                    source='main.storage')
                return data[:2]
            except Exception:
                log('Error: Failed to extract data from memory',
                    'ERROR', 'main.storage')
                log(traceback.format_exc(), 'ERROR', 'main.storage')
                return ({}, {})
    except FileNotFoundError:
        return ({}, {})


def extract_from_data(memory: Any) -> tuple[dict[int, List[TrackPlayer]], dict[int, int], List[AllottedFile]]:
    tracked_players = memory['tracked_players']
    output_channels = memory['output_channels']
    allotted_files = memory.get('allotted_files', [])

    tracked_players = {int(key): val for key,
                       val in tracked_players.items()}
    output_channels = {int(key): val for key,
                       val in output_channels.items()}

    for tracked in tracked_players.values():
        for user in tracked:
            user['claimed_users'] = set(user['claimed_users'])

    for file in allotted_files:
        file['expiry'] = datetime.fromisoformat(file['expiry'])

    return (tracked_players, output_channels, allotted_files)


def export_memory() -> str:
    with open(memory_path, 'r') as f:
        return f.read()


def write(tracked_players: dict[int, List[TrackPlayer]], output_channels: dict[int, int]):
    if tracked_players is None:
        tracked_players = write_memory['tracked_players']
        output_channels = write_memory['output_channels']
    else:
        write_memory['tracked_players'] = tracked_players
        write_memory['output_channels'] = output_channels

    with open(memory_path, 'w') as f:
        data = {'tracked_players': tracked_players,
                'output_channels': output_channels,
                'allotted_files': allotted_files}
        json.dump(data, f, cls=MemoryEncoder)
        log('Updated persistent memory', source='main.storage')


def clear_expired_files():
    for i in reversed(range(len(allotted_files))):
        file = allotted_files[i]
        if datetime.now() > file['expiry']:
            remove(file['path'])
            allotted_files.pop(i)


def allot_file(ext: str, life_span: timedelta = timedelta(hours=24)) -> AllottedFile:
    clear_expired_files()
    filename = f'{uuid4()}.{ext}'
    file = AllottedFile(
        name=filename,
        path=path.join(FILES_PATH, filename),
        expiry=datetime.now() + life_span)

    allotted_files.append(file)
    write(None, None)
    return file
