from typing import override
from utils import random_superlative, rank_assets
from .base import BaseGameEvent


class LowKDAEvent(BaseGameEvent):
    @override
    def embed(self):
        embed = super().embed(0xEE4B2B)
        embed.set_thumbnail(url=rank_assets[self.user.max_division.upper()])

        player = self.game.get_player(self.user.id)
        if player is None:
            return embed

        embed.add_field(
            name=f"{self.user.summoner_name} has achieved the {
                random_superlative()} KDA of {player.kda()} in a recent match!",
            value=f"They played as {player.champion_name} and the game lasted {
                round(self.game.duration / 60, 1)} mins and got a score of {player.score()}.",
            inline=False)

        return embed
