from typing import Literal, override
from riot import GameInfo, UserInfo, Rank
from utils import random_superlative, rank_assets
from .base import BaseGameEvent


class RankChangeEvent(BaseGameEvent):
    def __init__(self, user: UserInfo, game: GameInfo, old_rank: Rank, mode: Literal['Flex', 'Solo/Duo']):
        super().__init__(user, game)
        self.old_rank = old_rank
        self.new_rank = user.ranks[mode]
        self.mode = mode

    @override
    def embed(self):
        embed = super().embed(0x32CD32)
        embed.set_thumbnail(url=rank_assets[self.new_rank.division])

        embed.add_field(
            name=f"{self.user.summoner_name} has been {
                self.rank_dir()} from {self.old_rank.full()} to {self.new_rank.full()}",
            value=f"Make sure to congratulate them for this {
                random_superlative()} achievement!",
            inline=False)

        return embed

    def rank_dir(self):
        if self.old_rank.id() < self.new_rank.id():
            return 'promoted'
        else:
            return 'demoted'
