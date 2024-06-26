import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

LEAGUE_PATCH = "14.10.1"


@dataclass
class Config():
    RIOT_TOKEN: str
    DISCORD_TOKEN: str
    SERVER: str
    REGION: str
    FILES_PATH: str
    OWNER_DISCORD_ID: Optional[int]
    API_THREADS: int


def invalid_env(msg: str):
    print("Error: Invalid enviroment variables:")
    print(f'Error:  - {msg}')


global_stored_config: Optional[Config] = None


def get_config():
    global global_stored_config
    if global_stored_config is not None:
        return global_stored_config

    RIOT_TOKEN = os.getenv("RIOT_TOKEN")
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

    if RIOT_TOKEN is None or DISCORD_TOKEN is None:
        invalid_env('A necessary token is missing')
        exit(1)

    if os.getenv('RAILWAY_PROJECT_ID'):
        FILES_PATH = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
        if FILES_PATH is None:
            invalid_env('Required Railway Volume is not present')
            exit(1)
    else:
        FILES_PATH = os.getenv('FILES_PATH')
        if FILES_PATH is None:
            invalid_env('Missing file path for persistent storage')
            exit(1)
        if not os.path.exists(FILES_PATH):
            os.makedirs(FILES_PATH)

    OWNER_DISCORD_ID = os.getenv('OWNER_DISCORD_ID')
    if OWNER_DISCORD_ID is not None:
        try:
            OWNER_DISCORD_ID = int(OWNER_DISCORD_ID)
        except ValueError:
            invalid_env('OWNER_DISCORD_ID must be a number')
            exit(1)

    API_THREADS = os.getenv('API_THREADS', '5')
    if API_THREADS is not None:
        try:
            API_THREADS = int(API_THREADS)
        except ValueError:
            invalid_env('API_THREADS must be a number')
            exit(1)

    global_stored_config = Config(
        RIOT_TOKEN,
        DISCORD_TOKEN,
        os.getenv("SERVER", "euw1"),
        os.getenv("REGION", "europe"),
        FILES_PATH,
        OWNER_DISCORD_ID,
        API_THREADS
    )
    return global_stored_config
