import random


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
