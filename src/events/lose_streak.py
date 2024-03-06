from typing import override
from utils import random_superlative, rank_assets
from riot import GameInfo, UserInfo
from .base import BaseGameEvent


class LoseStreakEvent(BaseGameEvent):
    def __init__(self, user: UserInfo, game: GameInfo, streak: int):
        super().__init__(user, game)
        self.streak = streak

    @override
    def embed(self):
        embed = super().embed(0x59D5E0)
        embed.set_thumbnail(url=rank_assets[self.user.max_division.upper()])

        embed.add_field(
            name=f"{self.user.summoner_name} has just lost for the {
                self.streak}{'rd' if self.streak == 3 else 'th'} time in a row!",
            value=f"Make sure to congratulate them for this {
                random_superlative()} achievement!",
            inline=False)

        return embed
