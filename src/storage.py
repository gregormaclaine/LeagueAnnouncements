import json
from game_info import TrackPlayer
from typing import List
from os import path
from logs import log


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class Storage:
    FILENAME = 'memory.json'

    def __init__(self, files_path: str):
        self.path = files_path

    def read(self) -> tuple[dict[int, List[TrackPlayer]], dict[int, int]]:
        try:
            with open(path.join(self.path, self.FILENAME), 'r') as f:
                try:
                    memory = json.load(f)
                except json.decoder.JSONDecodeError:
                    log('Failed to decode persistent memory',
                        source='main.storage')
                    return ({}, {})

                try:
                    data = self.extract_from_data(memory)
                    log('Successfully loaded persistent memory',
                        source='main.storage')
                    return data
                except Exception as e:
                    log('Error: Failed to extract data from memory',
                        'ERROR', 'main.storage')
                    log(e, 'ERROR', 'main.storage')
                    return ({}, {})
        except FileNotFoundError:
            return ({}, {})

    def extract_from_data(self, memory: any) -> tuple[dict[int, List[TrackPlayer]], dict[int, int]]:
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

    def write(self, tracked_players: dict[int, List[TrackPlayer]], output_channels: dict[int, int]):
        with open(path.join(self.path, self.FILENAME), 'w') as f:
            data = {'tracked_players': tracked_players,
                    'output_channels': output_channels}
            json.dump(data, f, cls=SetEncoder)
            log('Updated persistent memory', source='main.storage')
