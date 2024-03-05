import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

LEAGUE_PATCH = "14.3.1"


@dataclass
class Config():
    RIOT_TOKEN: str
    DISCORD_TOKEN: str
    SERVER: str
    REGION: str
    FILES_PATH: str
    OWNER_DISCORD_ID: Optional[int]


def invalid_env(msg: str):
    print("Error: Invalid enviroment variables:")
    print(f'Error:  - {msg}')


def get_config():
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

    return Config(
        RIOT_TOKEN,
        DISCORD_TOKEN,
        os.getenv("SERVER", "euw1"),
        os.getenv("REGION", "europe"),
        FILES_PATH,
        OWNER_DISCORD_ID
    )
