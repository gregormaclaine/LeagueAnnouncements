import discord
import requests
import random
from typing import List
from game_info import UserInfo, TrackPlayer
from datetime import datetime
from events import GameEvent
from utils import random_superlative, repair_champ_name, num_of

rank_assets = {
    "UNRANKED": "https://cdn.discordapp.com/attachments/989905618494181386/989936020013334628/unranked.png",
    "IRON": "https://cdn.discordapp.com/attachments/989905618494181386/989905732445036614/iron.png",
    "BRONZE": "https://cdn.discordapp.com/attachments/989905618494181386/989905730805047356/bronze.png",
    "SILVER": "https://cdn.discordapp.com/attachments/989905618494181386/989905733128687626/silver.png",
    "GOLD": "https://cdn.discordapp.com/attachments/989905618494181386/989905731933311027/gold.png",
    "PLATINUM": "https://cdn.discordapp.com/attachments/989905618494181386/989905732856053851/platinum.png",
    "DIAMOND": "https://cdn.discordapp.com/attachments/989905618494181386/989905731463577600/diamond.png",
    "EMERALD": "https://cdn.discordapp.com/attachments/989905618494181386/1132067774584324096/emerald.png",
    "MASTER": "https://cdn.discordapp.com/attachments/989905618494181386/989905732654739516/master.png",
    "GRANDMASTER": "https://cdn.discordapp.com/attachments/989905618494181386/989905732176592956/grandmaster.png",
    "CHALLENGER": "https://cdn.discordapp.com/attachments/989905618494181386/989905731186749470/challenger.png",
}

league_patch = "14.3.1"


champion_info = requests.get(
    f"https://ddragon.leagueoflegends.com/cdn/{
        league_patch}/data/en_US/champion.json"
).json()
champion_name = {
    int(champion_info['data'][champion]['key']): repair_champ_name(champion)
    for champion in champion_info['data']
}


def icon_url(icon_id):
    return f"https://ddragon.leagueoflegends.com/cdn/{league_patch}/img/profileicon/{icon_id}.png"


def big_user(user: UserInfo):
    embed = discord.Embed(
        title=f"Level {user.level}",
        description=f"",
        color=random.randint(0, 16777215),
    )
    embed.set_author(name=user.summoner_name,
                     icon_url=icon_url(user.icon))
    embed.set_thumbnail(url=rank_assets[user.max_division.upper()])

    embed.add_field(
        name=f"Solo/Duo - {user.rank_solo}", value=user.solo_info())

    embed.add_field(name=f"Flex - {user.rank_flex}", value=user.flex_info())

    embed.add_field(
        name=f"Total Mastery: {user.total_mastery}",
        value=f" Total Points: {user.total_points:,}",
        inline=False
    )

    for champion in user.top_champs[:3]:
        name = champion_name.get(champion.id, f"ID: {champion.id}")
        embed.add_field(
            name=f"{name} ({champion.level} lvl)", value=f"{champion.points:,} pts."
        )

    return embed


def mini_user(user_info: UserInfo):
    embed = discord.Embed(
        title=f"Level {user_info.level}",
        description=f"",
        color=random.randint(0, 16777215),
    )
    embed.set_author(name=user_info.summoner_name,
                     icon_url=icon_url(user_info.icon))
    embed.set_thumbnail(url=rank_assets[user_info.max_division.upper()])
    embed.add_field(
        name=f"Total Mastery: {user_info.total_mastery}",
        value=f" Total Points: {user_info.total_points:,}",
        inline=False,
    )
    return embed


def tracked_list(users: List[TrackPlayer], offset: int):
    embed = discord.Embed(
        title=f"Tracking {num_of('Player', len(users))}",
        description=f"Showing players {
            offset * 15 + 1}-{min((offset + 1) * 15, len(users))}",
        color=random.randint(0, 16777215),
    )

    for i, u in enumerate(users[offset * 15:(offset + 1) * 15]):
        index = offset * 15 + i + 1
        user_line = f"{index}. {u['name']}#{u['tag']} (Lvl {u['level']})"
        embed.add_field(name=user_line, value="", inline=False)

    return embed


def announcement(e: GameEvent):
    embed = discord.Embed(
        title=f"Congratulations {e.user.summoner_name}!",
        description=f"",
        color=random.randint(0, 16777215),
    )
    embed.set_author(name=f'{e.user.summoner_name} (Lvl {e.user.level})',
                     icon_url=icon_url(e.user.icon))

    if e.kind == 'Rank Change':
        embed.set_thumbnail(url=rank_assets[e.new_rank.upper()])
    else:
        embed.set_thumbnail(url=rank_assets[e.user.max_division.upper()])

    if e.kind == 'KDA':
        player = e.game.get_player(e.user.id)
        embed.add_field(
            name=f"{e.user.summoner_name} has achieved the {
                random_superlative()} KDA of {e.kda} in a recent match!",
            value=f"They played as {e.champ} and the game lasted {
                round(e.game.duration / 60, 1)} mins and got a score of {player.score()}",
            inline=False)
    elif e.kind == 'Lose Streak':
        embed.add_field(
            name=f"{e.user.summoner_name} has just lost for the {
                e.streak}{'rd' if e.streak == 3 else 'th'} time in a row!",
            value=f"Make sure to congratulate them for this {
                random_superlative()} achievement!",
            inline=False)
    elif e.kind == 'Rank Change':
        embed.add_field(
            name=f"{e.user.summoner_name} has successfully {
                e.rank_dir()} to {e.new_rank.capitalize()} from {e.old_rank.capitalize()}!",
            value=f"Make sure to congratulate them for this {
                random_superlative()} achievement!",
            inline=False)

    time = datetime.fromtimestamp(e.game.start_time / 1000)\
        .strftime("%a, %d %b %Y %I:%M%p")
    embed.set_footer(text=f'Game played at {time}')

    return embed
