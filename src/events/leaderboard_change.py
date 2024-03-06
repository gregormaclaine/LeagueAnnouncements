from datetime import datetime
from typing import Literal, override

import discord
from riot import GameInfo, UserInfo
from utils import ordinal
from .base import BaseGameEvent


class LeaderboardChangeEvent(BaseGameEvent):
    mode: Literal['Solo/Duo', 'Flex']

    def __init__(self, position: int, old_user: UserInfo, new_user: UserInfo, last_game: GameInfo, mode: Literal['Solo/Duo', 'Flex']):
        super().__init__(new_user, last_game)
        self.position = position
        self.old_user = old_user
        self.new_user = new_user
        self.last_game = last_game
        self.mode = mode

    @override
    def embed(self):
        embed = discord.Embed(
            title=f"LEADERBOARD UPDATED!!",
            description=f"",
            color=0x581845,
        )

        embed.set_author(name=f'Leaderboard - {self.mode}')

        embed.add_field(name=f"{self.new_user.summoner_name} has overtaken {
                        self.old_user.summoner_name} for {ordinal(self.position)} place on the {self.mode} Leaderboard!", value='', inline=False)

        embed.add_field(name=f"{self.old_user.summoner_name} - {
                        self.old_user.ranks[self.mode].full()}",
                        value=self.old_user.ranks[self.mode].info())

        embed.add_field(name=f"{self.new_user.summoner_name} - {
                        self.new_user.ranks[self.mode].full()}",
                        value=self.new_user.ranks[self.mode].info())

        time = datetime.fromtimestamp(self.last_game.start_time / 1000)\
            .strftime("%a, %d %b %Y %I:%M%p")
        embed.set_footer(
            text=f'Game that likely led to this, played at {time}')

        return embed
