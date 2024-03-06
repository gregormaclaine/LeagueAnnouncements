import sys
from datetime import datetime
import discord
from colorist import Color, Effect
from utils import r_pad


def style(text: str, color: str = Color.DEFAULT, bold=False):
    return f'{color}{Effect.BOLD if bold else ""}{text}{Effect.BOLD_OFF}{Color.OFF}'


level_colors = {
    'INFO': Color.BLUE,
    'WARNING': Color.YELLOW,
    'ERROR': Color.RED,
    'COMMAND': Color.CYAN
}


def log(message, level="INFO", source='main'):
    timestamp_str = style(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), Color.BLACK, True)
    level_s = style(r_pad(level), level_colors.get(level, Color.GREEN), True)
    log_origin = style(source, Color.MAGENTA)
    out = sys.stdout if level != 'ERROR' else sys.stderr
    print(f"{timestamp_str} {level_s} {log_origin} {message}", file=out)


def log_command(i: discord.Interaction) -> None:
    if i.data is None or 'name' not in i.data:
        return

    log_s = f'[{i.data["name"]}]'

    if 'options' in i.data:
        options = " ".join([str(x['value'] if 'value' in x else None)
                           for x in i.data['options']])
        log_s += f' with options [{options}]'

    log_s += f' from [{i.user}] in guild [{i.guild}], channel [{i.channel}]'
    log(log_s, 'COMMAND')
