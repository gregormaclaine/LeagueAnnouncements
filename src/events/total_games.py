from typing import Literal, override
from riot import GameInfo, UserInfo, Rank
from utils import random_superlative, rank_assets
from .base import BaseGameEvent


class TotalGamesEvent(BaseGameEvent):
    def __init__(self, user: UserInfo, game: GameInfo, mode: Literal['Solo/Duo', 'Flex']):
        super().__init__(user, game)
        self.mode = mode

    @override
    def embed(self):
        embed = super().embed(0xff80c5)

        rank = self.user.ranks[self.mode]

        embed.set_thumbnail(url=rank_assets[rank.division])

        line1 = f"{self.user.summoner_name} has officially completed their {
            rank.games()}th game!!"

        line2 = f"What a truly {random_superlative()} commitment to the game!"

        embed.add_field(name=line1, value=line2, inline=False)

        rank_cutoff = Rank('GOLD', 'IV', 0, 0, 0)
        if rank.id() < rank_cutoff.id():
            line1 = f"Through this dedication, {
                self.user.summoner_name} has achieved a rank of {rank.full()}."

            line2 = f"What {random_superlative()} dedication to the game!"
            embed.add_field(name=line1, value=line2, inline=False)

        return embed
