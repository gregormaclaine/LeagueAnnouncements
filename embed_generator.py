import discord
import requests
import random
from typing import List
from game_info import UserInfo

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


def repair_champ_name(champ_name):
    new_champ_name = ""
    for i in champ_name:
        if i <= "Z" and new_champ_name != "":
            new_champ_name += " " + i
        else:
            new_champ_name += i
    return new_champ_name


champion_info = requests.get(
    f"https://ddragon.leagueoflegends.com/cdn/{league_patch}/data/en_US/champion.json"
).json()
champion_name = {
    int(champion_info['data'][champion]['key']): repair_champ_name(champion)
    for champion in champion_info['data']
}


def icon_url(icon_id):
    return f"https://ddragon.leagueoflegends.com/cdn/{league_patch}/img/profileicon/{icon_id}.png"


def big_user(user_info: UserInfo):
    embed = discord.Embed(
        title=f"Level {user_info.level}",
        description=f"",
        color=random.randint(0, 16777215),
    )
    embed.set_author(name=user_info.summoner_name,
                     icon_url=icon_url(user_info.icon))
    embed.set_thumbnail(url=rank_assets[user_info.max_division.upper()])
    embed.add_field(
        name=f"Solo/Duo - {user_info.rank_solo}",
        value=f"{str(user_info.lp_solo) + ' LP, ' if user_info.rank_solo != 'UNRANKED' else ''}{user_info.wins_solo + user_info.losses_solo} games{f', {round(user_info.wins_solo/(user_info.losses_solo + user_info.wins_solo) * 100, 2)}% WR' if (user_info.losses_solo + user_info.wins_solo) > 0 else ''}",
    )
    embed.add_field(
        name=f"Flex - {user_info.rank_flex}",
        value=f"{str(user_info.lp_flex) + ' LP, ' if user_info.rank_flex != 'UNRANKED' else ''}{user_info.wins_flex + user_info.losses_flex} games{f', {round(user_info.wins_flex/(user_info.losses_flex + user_info.wins_flex) * 100, 2)}% WR' if (user_info.losses_flex + user_info.wins_flex) > 0 else ''}",
    )
    embed.add_field(
        name=f"Total Mastery: {user_info.total_mastery}",
        value=f" Total Points: {user_info.total_points:,}",
        inline=False
    )
    for champion in user_info.top_champs[:3]:
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


def tracked_list(users: List[UserInfo], offset: int, total: int):
    embed = discord.Embed(
        title=f"Tracking {len(users)} Player{'s' if len(users) != 1 else ''}",
        description=f"Showing players {offset * 15 + 1}-{min((offset + 1) * 15, total)}",
        color=random.randint(0, 16777215),
    )

    for i, u in enumerate(users):
        index = offset * 15 + i + 1
        user_line = f"{index}. {u.summoner_name} (Lvl {u.level})"
        embed.add_field(name=user_line, value="", inline=False)

    return embed
