import random
from datetime import datetime


def flat(matrix):
    return [item for row in matrix for item in row]


def r_pad(t: str, w: int = 8):
    if len(t) >= w:
        return t
    return t + ' ' * (w - len(t))


def num_of(s: str, count: int):
    return f'{count} {s}{'s' if count != 1 else ''}'


def repair_champ_name(champ_name):
    new_champ_name = ""
    for i in champ_name:
        if i <= "Z" and new_champ_name != "":
            new_champ_name += " " + i
        else:
            new_champ_name += i
    return new_champ_name


def cache_with_timeout(seconds: int = 120):
    def decorator(func):
        cache: dict[tuple, tuple[datetime, any]] = {}

        async def wrapper(*args, **kwargs):
            cached = cache.get(args)
            if cached:
                # print(f'Hit cache - {func.__name__}')
                if (datetime.now() - cached[0]).seconds <= seconds:
                    return cached[1]
                # print(f'Cache timout - {func.__name__}')
                del cache[args]

            # print(f'Running call - {func.__name__}')
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
