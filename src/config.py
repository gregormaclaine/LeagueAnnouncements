import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
load_dotenv()


@dataclass
class Config():
    RIOT_TOKEN: str
    DISCORD_TOKEN: str
    SERVER: str
    REGION: str
    FILES_PATH: str
    OWNER_DISCORD_ID: Optional[int]


def get_config():
    RIOT_TOKEN = os.getenv("RIOT_TOKEN")
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

    if RIOT_TOKEN is None or DISCORD_TOKEN is None:
        print("Error: Invalid enviroment variables:")
        print('Error:  - a necessary token is missing')
        exit(1)

    if os.getenv('RAILWAY_PROJECT_ID'):
        FILES_PATH = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
        if FILES_PATH is None:
            print('Error: Required Railway Volume is not present')
            exit(1)
    else:
        FILES_PATH = os.getenv('FILES_PATH')
        if FILES_PATH is None:
            print('Error: Invalid environment variables')
            print('Error:  - missing file path for persistent storage')
            exit(1)
        if not os.path.exists(FILES_PATH):
            os.makedirs(FILES_PATH)

    try:
        OWNER_DISCORD_ID = int(os.getenv('OWNER_DISCORD_ID'))
    except TypeError:
        OWNER_DISCORD_ID = None

    return Config(
        RIOT_TOKEN,
        DISCORD_TOKEN,
        os.getenv("SERVER", "euw1"),
        os.getenv("REGION", "europe"),
        FILES_PATH,
        OWNER_DISCORD_ID
    )
