import discord
from datetime import datetime
from colorist import Color, Effect


def r_pad(t: str, w: int = 8):
    if len(t) >= w:
        return t
    return t + ' ' * (w - len(t))


def style(text: str, color: Color = Color.DEFAULT, bold=False):
    return f'{color}{Effect.BOLD if bold else ""}{text}{Effect.BOLD_OFF}{Color.OFF}'


level_colors = {
    'INFO': Color.BLUE,
    'WARNING': Color.YELLOW,
    'ERROR': Color.RED,
    'COMMAND': Color.CYAN
}


def log(message, level="INFO"):
    timestamp_str = style(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), Color.BLACK, True)
    level_s = style(r_pad(level), level_colors.get(level, Color.GREEN), True)
    log_origin = style('main', Color.MAGENTA)
    print(f"{timestamp_str} {level_s} {log_origin} {message}")


def log_command(i: discord.Interaction):
    log_s = f'[{i.data["name"]}]'

    if 'options' in i.data:
        options = " ".join([str(x['value']) for x in i.data['options']])
        log_s += f' with options [{options}]'

    log_s += f' from [{i.user}] in guild [{i.guild}], channel [{i.channel}]'
    log(log_s, 'COMMAND')
