import discord
import requests
import random
from typing import List, Literal
from event_manager import OrderedUserRank
from storage import TrackPlayer
from riot import UserInfo
from utils import icon_url, r_pad, repair_champ_name, num_of, rank_assets
from logs import log
from config import LEAGUE_PATCH

champion_info = requests.get(
    f"https://ddragon.leagueoflegends.com/cdn/{
        LEAGUE_PATCH}/data/en_US/champion.json"
).json()
champion_name = {
    int(champion_info['data'][champion]['key']): repair_champ_name(champion)
    for champion in champion_info['data']
}


def big_user(user: UserInfo):
    embed = discord.Embed(
        title=f"Level {user.level}",
        description=f"",
        color=random.randint(0, 16777215),
    )
    embed.set_author(name=user.summoner_name,
                     icon_url=icon_url(user.icon))
    embed.set_thumbnail(url=rank_assets[user.max_division.upper()])

    for mode, rank in user.ranks.items():
        embed.add_field(name=f"{mode} - {rank.full()}", value=rank.info())

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
        links = '🔗' * len(u['claimed_users'])
        user_line = f"{index}. {u['name']}#{
            u['tag']} (Lvl {u['level']})  {links}"
        embed.add_field(name=user_line, value="", inline=False)

    return embed


def leaderboard(mode: Literal['Solo/Duo', 'Flex'], ranked_players: List[OrderedUserRank], tracked_players: List[TrackPlayer]):
    embed = discord.Embed(
        title=f"Leaderboard - {mode}",
        description=f"",
        color=random.randint(0, 16777215),
    )

    max_len = max(map(len, (p["name"] for p in tracked_players)))

    for i, p in enumerate(ranked_players):
        matches = [tp for tp in tracked_players if tp["puuid"] == p["puuid"]]
        if len(matches) == 0:
            log(
                f"Couldn't find event-memorised player in tracked_players (puuid={p['puuid']})", 'ERROR', 'main.embeds')
            continue
        tp = matches[0]

        line = r_pad(f'{i + 1}. {tp['name']}#{tp['tag']}', max_len + 10)
        line += f"({p['rank'].full()}: LP = {p['rank'].lp})"

        if i < 3:
            line = f'**{line}**'

        embed.add_field(name=line, value='', inline=False)

    return embed
