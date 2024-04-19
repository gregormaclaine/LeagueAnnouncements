import json
import traceback
from os import path
from typing import Any, List, TypedDict
from logs import log
from config import get_config

FILENAME = 'memory.json'

FILES_PATH = get_config().FILES_PATH
memory_path = path.join(FILES_PATH, FILENAME)


class SetEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return json.JSONEncoder.default(self, o)


class TrackPlayer(TypedDict):
    puuid: str
    name: str
    tag: str
    level: int
    claimed_users: set[int]


def read() -> tuple[dict[int, List[TrackPlayer]], dict[int, int]]:
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
                log('Successfully loaded persistent memory',
                    source='main.storage')
                return data
            except Exception:
                log('Error: Failed to extract data from memory',
                    'ERROR', 'main.storage')
                log(traceback.format_exc(), 'ERROR', 'main.storage')
                return ({}, {})
    except FileNotFoundError:
        return ({}, {})


def extract_from_data(memory: Any) -> tuple[dict[int, List[TrackPlayer]], dict[int, int]]:
    tracked_players = memory['tracked_players']
    output_channels = memory['output_channels']

    tracked_players = {int(key): val for key,
                       val in tracked_players.items()}
    output_channels = {int(key): val for key,
                       val in output_channels.items()}

    for tracked in tracked_players.values():
        for user in tracked:
            user['claimed_users'] = set(user['claimed_users'])

    return (tracked_players, output_channels)


def write(tracked_players: dict[int, List[TrackPlayer]], output_channels: dict[int, int]):
    with open(memory_path, 'w') as f:
        data = {'tracked_players': tracked_players,
                'output_channels': output_channels}
        json.dump(data, f, cls=SetEncoder)
        log('Updated persistent memory', source='main.storage')
