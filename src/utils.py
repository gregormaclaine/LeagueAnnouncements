import random
from datetime import datetime
from typing import Any
from config import LEAGUE_PATCH


def flat(matrix):
    return [item for row in matrix for item in row]


def r_pad(t: str, w: int = 8):
    if len(t) >= w:
        return t
    return t + ' ' * (w - len(t))


def num_of(s: str, count: int):
    return f'{count} {s}{'s' if count != 1 else ''}'


def ordinal(num: int):
    if num < 4:
        return ['0th', '1st', '2nd', '3rd'][num]
    return f'{num}th'


def repair_champ_name(champ_name):
    new_champ_name = ""
    for i in champ_name:
        if i <= "Z" and new_champ_name != "":
            new_champ_name += " " + i
        else:
            new_champ_name += i
    return new_champ_name


def icon_url(icon_id):
    return f"https://ddragon.leagueoflegends.com/cdn/{LEAGUE_PATCH}/img/profileicon/{icon_id}.png"


def cache_with_timeout(seconds: int = 120):
    def decorator(func):
        cache: dict[tuple, tuple[datetime, Any]] = {}

        async def wrapper(*args, **kwargs):
            cached = cache.get(args)
            if cached:
                # print(f'Cache ✅ - {func.__name__}{args[1:]}')
                if (datetime.now() - cached[0]).seconds <= seconds:
                    return cached[1]
                # print(f'Cache 🕒 - {func.__name__}{args[1:]}')
                del cache[args]

            # print(f'Cache ⏩ - {func.__name__}{args[1:]}')
            data = await func(*args, **kwargs)
            cache[args] = (datetime.now(), data)
            return data

        return wrapper
    return decorator


def random_superlative():
    return random.choice([
        'incredible',
        'amazing',
        'unbelievable',
        'impossible',
        'astounding',
        'astonishing',
        'stunning',
        'bewildering',
        'staggering',
        'breathtaking',
        'stupefying',
        'awe-inspiring',
        'marvelous',
        'mind-blowing',
        'spectacular',
        'prodigious',
        'extraordinary'
    ])


def random_celebration():
    return random.choice([
        'Congratulations',
        'Well Done',
        'Compliments to',
        'Everyone Applaud',
        'Let\'s Cheer for',
        '<sup> Job,',
        '<sup> Work,'
    ]).replace('<sup>', random_superlative().capitalize())


rank_assets = {
    "UNRANKED": "https://cdn.discordapp.com/attachments/989905618494181386/989936020013334628/unranked.png",
    "IRON": "https://cdn.discordapp.com/attachments/989905618494181386/989905732445036614/iron.png",
    "BRONZE": "https://cdn.discordapp.com/attachments/989905618494181386/989905730805047356/bronze.png",
    "SILVER": "https://cdn.discordapp.com/attachments/989905618494181386/989905733128687626/silver.png",
    "GOLD": "https://cdn.discordapp.com/attachments/989905618494181386/989905731933311027/gold.png",
    "PLATINUM": "https://cdn.discordapp.com/attachments/989905618494181386/989905732856053851/platinum.png",
    "DIAMOND": "https://cdn.discordapp.com/attachments/989905618494181386/989905731463577600/diamond.png",
    "EMERALD": "https://cdn.discordapp.com/attachments/989905618494181386/1132067774584324096/emerald.png",
    "MASTER": "https://cdn.discordapp.com/attachments/989905618494181386/989905732654739516/master.png",
    "GRANDMASTER": "https://cdn.discordapp.com/attachments/989905618494181386/989905732176592956/grandmaster.png",
    "CHALLENGER": "https://cdn.discordapp.com/attachments/989905618494181386/989905731186749470/challenger.png",
}


banner_art = r"""
   __                                 ___       _   
  / /  ___  __ _  __ _ _   _  ___    / __\ ___ | |_ 
 / /  / _ \/ _` |/ _` | | | |/ _ \  /__\/// _ \| __|
/ /__|  __/ (_| | (_| | |_| |  __/ / \/  \ (_) | |_ 
\____/\___|\__,_|\__, |\__,_|\___| \_____/\___/ \__|
                 |___/                              
"""


def print_header():
    print('| ' + banner_art[1:].replace('\n', '\n| '))
