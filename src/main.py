import discord
from discord.ext import commands as discord_commands, tasks
from dotenv import load_dotenv
import os
import embed_generator
from riot.api import RiotAPI
from logs import log, log_command
from events import EventManager
from game_info import UserInfo

load_dotenv()

RIOT_TOKEN = os.getenv("RIOT_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if RIOT_TOKEN is None or DISCORD_TOKEN or None:
    print("Error: Invalid enviroment variables:")
    print('Error:  - a necessary token is missing')
    exit(1)


def main():
    intents = discord.Intents.default()

    tracked_players = {}
    output_channels = {}

    # Riot API constants
    server = os.getenv("SERVER", "euw1")
    region = os.getenv("REGION", "europe")

    bot = discord_commands.Bot(command_prefix="!", intents=intents)
    riot_client = RiotAPI(RIOT_TOKEN, server, region)
    events = EventManager(riot_client)

    async def get_user_from_name(interaction: discord.Interaction, name: str, tag: str):
        puuid_res = await riot_client.get_riot_account_puuid(name, tag)
        if puuid_res.error() == 'not-found':
            await interaction.response.send_message(f"Riot Account {name}#{tag} doesn't exist")
            return None
        if await puuid_res.respond_if_error(interaction.response.send_message):
            return None

        data_res = await riot_client.get_profile_info(puuid_res.data["puuid"])
        if data_res.error() == 'not-found':
            await interaction.response.send_message(f"Summoner {name}#{tag} doesn't exist")
            return None
        if await puuid_res.respond_if_error(interaction.response.send_message):
            return None

        return data_res.data

    @bot.event
    async def on_ready():
        await bot.tree.sync()
        log(f"Logged in as {bot.user} (ID: {bot.user.id})")
        await bot.change_presence(
            status=discord.Status.online, activity=discord.Game(
                "League of Legends")
        )
        log('Starting automatic announcement checker')
        await automatic_announcement_check.start()

    @bot.tree.command(name="track", description="Tracks a player")
    async def track(interaction: discord.Interaction, name: str, tag: str):
        log_command(interaction)
        user = await get_user_from_name(interaction, name, tag)
        if user is None:
            return

        g_id = interaction.guild_id
        if g_id in tracked_players:
            tracked_players[g_id].append(user.puuid)
        else:
            tracked_players[g_id] = [user.puuid]

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
        if data.error():
            await interaction.response.send_message("Stopped tracking unknown player")
        else:
            await interaction.response.send_message(f"Stopped tracking {data.data.summoner_name}")

    @bot.tree.command(name="list", description="Lists all tracked players")
    async def list(interaction: discord.Interaction, offset: int = 0):
        log_command(interaction)

        if offset < 0:
            log(tracked_players)
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
            if data.error():
                log(f'Couldn\'t find tracked profile (puuid={puuid})', 'ERROR')
                log(data.data, 'ERROR')
                users.append(UserInfo(summoner_name=f'Unknown<{puuid[:15]}>'))
            else:
                users.append(data.data)

        embed = embed_generator.tracked_list(users, offset, len(tracked))
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="profile", description="Shows profile of a player")
    async def profile(interaction: discord.Interaction, name: str, tag: str):
        log_command(interaction)
        user = await get_user_from_name(interaction, name, tag)
        if user:
            await interaction.response.send_message(embed=embed_generator.big_user(user))

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

    # @bot.tree.command(name="dev_set_game_mem", description="Don't touch this")
    # async def dev_set_game_mem(interaction: discord.Interaction, puuid: str, game_id: str):
    #     await interaction.response.defer()
    #     log_command(interaction)

    #     success = await events.set_memory_to_game(puuid, game_id)
    #     await interaction.followup.send('Success' if success else 'Failed')

    @bot.tree.command(name="set_channel", description="Set the channel for announcements to appear")
    async def set_channel(interaction: discord.Interaction, channel_id: str):
        log_command(interaction)
        old_id = output_channels.get(interaction.guild_id, None)

        channel = bot.get_channel(int(channel_id))
        if channel is None:
            await interaction.response.send_message('Channel not found')
            return

        output_channels[interaction.guild_id] = int(channel_id)

        await interaction.response.send_message(
            'Channel Updated' if old_id else 'Channel Set')

        await channel.send('I will now send announcements here')

    @tasks.loop(seconds=300)  # repeat after every 5 mins
    async def automatic_announcement_check():
        for guild_id, channel_id in output_channels.items():
            if guild_id not in tracked_players:
                continue
            announcments = await events.check(tracked_players[guild_id])

            if len(announcments) == 0:
                continue

            embeds = [embed_generator.announcement(e) for e in announcments]
            await bot.get_channel(channel_id).send(embeds=embeds)

    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
