import random
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Literal
import discord
from riot import GameInfo, UserInfo
from utils import icon_url, random_celebration


@dataclass
class BaseGameEvent:
    user: UserInfo
    game: GameInfo
    type: Literal['embed', 'image'] = 'embed'

    def embed(self, color: Optional[int] = None):
        embed = discord.Embed(
            title=f"{random_celebration()} {self.user.summoner_name}!",
            description=f"",
            color=random.randint(0, 16777215) if color is None else color,
        )
        embed.set_author(name=f'{self.user.summoner_name} (Lvl {self.user.level})',
                         icon_url=icon_url(self.user.icon))

        time = datetime.fromtimestamp(self.game.start_time / 1000)\
            .strftime("%a, %d %b %Y %I:%M%p")
        embed.set_footer(text=f'Game played at {time}')

        return embed

    def image(self) -> str:
        return ''
