from typing import Literal, override
from riot import RiotAPI, GameInfo, RankOption, UserInfo
from utils import random_superlative, rank_assets
from .base import BaseGameEvent


class RankChangeEvent(BaseGameEvent):
    def __init__(self, user: UserInfo, game: GameInfo, old_rank: RankOption, mode: Literal['Flex', 'Solo/Duo']):
        super().__init__(user, game)
        self.old_rank = old_rank
        self.new_rank = user.rank_flex if mode == 'Flex' else user.rank_solo
        self.mode = mode

    @override
    def embed(self):
        embed = super().embed()
        rank = self.new_rank.split(' ')[0]
        embed.set_thumbnail(url=rank_assets[rank.upper()])

        embed.add_field(
            name=f"{self.user.summoner_name} has been {
                self.rank_dir()} from {self.old_rank.upper()} to {self.new_rank.upper()}!",
            value=f"Make sure to congratulate them for this {
                random_superlative()} achievement!",
            inline=False)

        return embed

    def rank_dir(self):
        if RiotAPI.is_rank_growth(self.old_rank, self.new_rank):
            return 'promoted'
        else:
            return 'demoted'
