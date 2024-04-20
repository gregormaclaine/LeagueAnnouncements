from typing import Literal, override
from riot import GameInfo, UserInfo, Rank
import discord
from utils import random_superlative, rank_assets
from .base import BaseGameEvent
from img_gen import generate_certificate
from storage import allot_file


class TotalGamesEvent(BaseGameEvent):
    def __init__(self, user: UserInfo, game: GameInfo, mode: Literal['Solo/Duo', 'Flex']):
        super().__init__(user, game)
        self.mode = mode
        self.type = 'image'

    @override
    def image(self) -> str:
        file = allot_file('png')
        generate_certificate(file['path'], self.user,
                             self.user.ranks[self.mode])
        return file['path']

    @override
    def embed(self):
        embed = discord.Embed(
            title=f"!! MAJOR GAME MILESTONE REACHED !!",
            description=f"",
            color=0xff80c5,
        )

        embed.set_author(name=f'Milestones - {self.mode}')

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
