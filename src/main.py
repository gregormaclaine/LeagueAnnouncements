import discord
from discord.ext import commands as discord_commands
from dotenv import load_dotenv
import os
import embed_generator
import riot_api
from logs import log, log_command
from events import EventManager


def riot_account_not_found(gameName, tag):
    return f"Riot Account {gameName}#{tag} doesn't exist"


def summoner_not_found(gameName, tag):
    return f"Summoner {gameName}#{tag} doesn't exist"


def main():
    load_dotenv()
    intents = discord.Intents.default()

    tracked_players = {}

    # Riot API constants
    server = os.getenv("SERVER", "euw1")
    region = os.getenv("REGION", "europe")

    bot = discord_commands.Bot(command_prefix="!", intents=intents)
    riot_client = riot_api.RiotAPI(os.getenv("RIOT_TOKEN"), server, region)
    events = EventManager(riot_client)

    @bot.event
    async def on_ready():
        await bot.tree.sync()
        log(f"Logged in as {bot.user} (ID: {bot.user.id})")
        await bot.change_presence(
            status=discord.Status.online, activity=discord.Game(
                "League of Legends")
        )

    @bot.tree.command(name="track", description="Tracks a player")
    async def track(interaction: discord.Interaction, name: str, tag: str):
        log_command(interaction)
        puuid = await riot_client.get_riot_account_puuid(name, tag)
        if puuid is None:
            await interaction.response.send_message(riot_account_not_found(name, tag))
            return

        data = await riot_client.get_profile_info(puuid)
        if data["status_code"] != 200:
            await interaction.response.send_message(summoner_not_found(name, tag))
            return

        user = data["user"]

        g_id = interaction.guild_id
        if g_id in tracked_players:
            tracked_players[g_id].append(puuid)
        else:
            tracked_players[g_id] = [puuid]

        await interaction.response.send_message(
            f'Began tracking {user.summoner_name}#{tag}.',
            embed=embed_generator.mini_user(user)
        )

    @bot.tree.command(name="untrack", description="Stops tracking a player")
    async def untrack(interaction: discord.Interaction, index: int):
        log_command(interaction)

        if index < 1:
            await interaction.response.send_message(f'Index must be a non-negative integer')
            return

        g_id = interaction.guild_id
        if g_id not in tracked_players:
            await interaction.response.send_message(f'No players are being tracked')
            return
        tracked = tracked_players[g_id]

        if index > len(tracked):
            await interaction.response.send_message(f'Index is out of range')
            return

        puuid = tracked.pop(index - 1)

        if len(tracked) == 0:
            del tracked_players[g_id]

        data = await riot_client.get_profile_info(puuid)
        if data["status_code"] != 200:
            await interaction.response.send_message("Stopped tracking unknown player")
        else:
            await interaction.response.send_message(f"Stopped tracking {data['user'].summoner_name}")

    @bot.tree.command(name="list", description="Lists all tracked players")
    async def list(interaction: discord.Interaction, offset: int = 0):
        log_command(interaction)

        if offset < 0:
            await interaction.response.send_message('Offset can\'t be negative')
            return

        g_id = interaction.guild_id
        if g_id not in tracked_players:
            await interaction.response.send_message(f'No players are being tracked')
            return
        tracked = tracked_players[g_id]

        await interaction.response.defer()

        users = []
        for puuid in tracked[offset * 15:(offset + 1) * 15]:
            data = await riot_client.get_profile_info(puuid)
            if data["status_code"] != 200:
                await interaction.followup.send('Couldn\'t find one of the profiles')
                return
            users.append(data["user"])

        embed = embed_generator.tracked_list(users, offset, len(tracked))
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="profile", description="Shows profile of a player")
    async def profile(interaction: discord.Interaction, name: str, tag: str):
        log_command(interaction)

        puuid = await riot_client.get_riot_account_puuid(name, tag)
        if puuid is None:
            await interaction.response.send_message(riot_account_not_found(name, tag))
            return

        data = await riot_client.get_profile_info(puuid)
        if data["status_code"] != 200:
            await interaction.response.send_message(summoner_not_found(name, tag))
        else:
            await interaction.response.send_message(embed=embed_generator.big_user(data["user"]))

    @bot.tree.command(name="run_checks", description="Manually check for new announcements")
    async def run_checks(interaction: discord.Interaction):
        log_command(interaction)

        g_id = interaction.guild_id
        if g_id not in tracked_players:
            await interaction.response.send_message(f'No players are being tracked')
            return
        tracked = tracked_players[g_id]

        await interaction.response.defer()

        announcments = await events.check(tracked)

        if len(announcments) == 0:
            await interaction.followup.send('No new announcements')
            return

        embeds = [embed_generator.announcement(e) for e in announcments]
        await interaction.followup.send(embeds=embeds)

    @bot.tree.command(name="dev_set_game_mem", description="Don't touch this")
    async def dev_set_game_mem(interaction: discord.Interaction, puuid: str, game_id: str):
        await interaction.response.defer()
        log_command(interaction)

        success = await events.set_memory_to_game(puuid, game_id)
        await interaction.followup.send('Success' if success else 'Failed')

    bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
