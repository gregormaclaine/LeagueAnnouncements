from math import ceil
import traceback
import discord
from discord.ext import commands as discord_commands, tasks
from typing import List, Literal, Optional, cast
import embed_generator
from events import BaseGameEvent
from riot import RiotAPI
from logs import log, log_command
from event_manager import EventManager
from utils import num_of, flat, print_header
from config import get_config
from storage import Storage


def main():
    print_header()
    CONFIG = get_config()
    intents = discord.Intents.default()

    storage = Storage(CONFIG.FILES_PATH)

    tracked_players, output_channels = storage.read()

    bot = discord_commands.Bot(command_prefix="!", intents=intents)
    riot_client = RiotAPI(CONFIG.RIOT_TOKEN, CONFIG.SERVER,
                          CONFIG.REGION, CONFIG.API_THREADS)
    events = EventManager(riot_client)

    def get_mentions_from_events(events: List[BaseGameEvent], guild_id: int) -> str:
        puuids = [e.user.puuid for e in events]
        tracked = tracked_players[guild_id]
        discord_ids = flat([t['claimed_users']
                           for t in tracked if t['puuid'] in puuids])
        return ' '.join(map(lambda id: f'<@{id}>', [*set(discord_ids)]))

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
        log(f"Logged in as {bot.user} (ID: {bot.user.id if bot.user else ''})")
        await bot.change_presence(
            status=discord.Status.online, activity=discord.Game(
                "League of Legends")
        )

        for tracked in tracked_players.values():
            await events.check([p['puuid'] for p in tracked], quiet=True)

        log('Starting automatic announcement checker')
        if not automatic_announcement_check.is_running():
            await automatic_announcement_check.start()

    @bot.tree.command(name="track", description="Tracks a player")
    async def track(interaction: discord.Interaction, name: str, tag: str):
        log_command(interaction)
        user = await get_user_from_name(interaction, name, tag)
        if user is None:
            return

        g_id = interaction.guild_id
        if g_id is None:
            await interaction.response.send_message(f'Could not get guild id')
            return

        if g_id in tracked_players:
            matches = [p for p in tracked_players[g_id]
                       if p["puuid"] == user.puuid]
            if len(matches):
                await interaction.response.send_message(f'Already tracking {user.summoner_name}#{tag.upper()}')
                return
        else:
            tracked_players[g_id] = []

        tracked_players[g_id].append({
            'puuid': user.puuid,
            'name': user.summoner_name,
            'tag': tag.upper(),
            'level': user.level,
            'claimed_users': set()
        })

        await interaction.response.send_message(
            f'Began tracking {user.summoner_name}#{tag}.',
            embed=embed_generator.mini_user(user)
        )
        await events.check([user.puuid], quiet=True)
        storage.write(tracked_players, output_channels)

    @bot.tree.command(name="track_many", description="Tracks multiple players at once (For dev use)")
    async def track_many(interaction: discord.Interaction, names: str):
        log_command(interaction)

        g_id = interaction.guild_id
        if g_id is None:
            await interaction.response.send_message(f'Could not get guild id')
            return

        if g_id not in tracked_players:
            tracked_players[g_id] = []

        name_list = names.split(',')
        if len(name_list) > 5:
            await interaction.response.defer()

        added_puuids = []
        for summoner in name_list:
            try:
                name, tag = summoner.split('#')
                if name == '' or tag == '':
                    raise ValueError(f'Name: [{name}], Tag: [{tag}]')
            except ValueError:
                await interaction.response.send_message('Error: Invalid request')
                return

            user = await get_user_from_name(interaction, name, tag)
            if user is None:
                return

            matches = [p for p in tracked_players[g_id]
                       if p["puuid"] == user.puuid]
            if len(matches):
                continue

            tracked_players[g_id].append({
                'puuid': user.puuid,
                'name': user.summoner_name,
                'tag': tag.upper(),
                'level': user.level,
                'claimed_users': set()
            })
            added_puuids.append(user.puuid)

        message = f'Request handled successfully: {
            num_of('player', len(added_puuids))} added'
        if len(name_list) > 5:
            await interaction.followup.send(message)
        else:
            await interaction.response.send_message(message)

        await events.check(added_puuids, quiet=True)
        storage.write(tracked_players, output_channels)

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

        deleted_player = tracked.pop(index - 1)

        if len(tracked) == 0:
            del tracked_players[g_id]

        player_name = f"{deleted_player['name']}#{deleted_player['tag']}"
        await interaction.response.send_message(f"Stopped tracking {player_name}")
        storage.write(tracked_players, output_channels)

    @bot.tree.command(name="list", description="Lists all tracked players")
    async def list(interaction: discord.Interaction, offset: int = 0):
        log_command(interaction)

        if offset < 0:
            log(tracked_players)
            print(events.get_ordered_solo_rankings())
            await interaction.response.send_message('Offset can\'t be negative')
            return

        g_id = interaction.guild_id
        if g_id not in tracked_players:
            await interaction.response.send_message(f'No players are being tracked')
            return
        tracked = tracked_players[g_id]

        embed = embed_generator.tracked_list(tracked, offset)
        await interaction.response.send_message(embed=embed)

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

        announcments = await events.check([p['puuid'] for p in tracked])

        if len(announcments) == 0:
            await interaction.followup.send('No new announcements')
            return

        embeds = [e.embed() for e in announcments]
        mentions = get_mentions_from_events(announcments[:10], g_id)
        if len(embeds) > 10:
            mentions += f' (And {num_of('other announcement',
                                        len(embeds) - 10)}...)'
        await interaction.followup.send(mentions, embeds=embeds[:10])

    @bot.tree.command(name="rollback_memory", description="Resets tracking to before a certain number of games for a user")
    async def rollback_memory(interaction: discord.Interaction, username: Optional[str] = None, games: int = 1):
        log_command(interaction)
        if interaction.user.id != CONFIG.OWNER_DISCORD_ID:
            await interaction.response.send_message('You do not have the permissions to use this command')
            return

        if games < 1:
            await interaction.response.send_message('Cannot rollback memory into future')
            return

        g_id = interaction.guild_id
        if g_id not in tracked_players:
            await interaction.response.send_message(f'No players are being tracked')
            return
        tracked = tracked_players[g_id]

        await interaction.response.defer()

        puuids = [(f"{u['name']}#{u['tag']}", u['puuid'])
                  for u in tracked if username is None or u['name'].lower() == username.lower()]

        result = f'Result (Matched {num_of("User", len(puuids))}){
            ":" if puuids else ""}'
        for name, puuid in puuids:
            success = await events.set_memory_to_game(puuid, offset=games)
            result += f'\n- {name}: {"Success" if success else 'Failed'}'

        await interaction.followup.send(result)

    @bot.tree.command(name="set_channel", description="Set the channel for announcements to appear")
    async def set_channel(interaction: discord.Interaction, channel_id: str, silent: bool = False):
        log_command(interaction)
        if interaction.guild_id is None:
            await interaction.response.send_message(f'Could not get guild id')
            return
        old_id = output_channels.get(interaction.guild_id, None)

        try:
            channel = bot.get_channel(int(channel_id))
        except:
            await interaction.response.send_message('Could not access channel')
            return
        if channel is None:
            await interaction.response.send_message('Channel not found')
            return
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(f'Channel must be a public text channel')
            return

        output_channels[interaction.guild_id] = int(channel_id)

        await interaction.response.send_message(
            'Channel Updated' if old_id else 'Channel Set')

        if not silent:
            await channel.send('I will now send announcements here')
        storage.write(tracked_players, output_channels)

    @bot.tree.command(name="autochecker", description="Inspect and modify the automatic checker")
    async def autochecker(interaction: discord.Interaction, command: Literal['status', 'pause', 'unpause', 'start']):
        log_command(interaction)
        is_running = automatic_announcement_check.is_running()
        next_time = automatic_announcement_check.next_iteration

        if command == 'status':
            current_loop = automatic_announcement_check.current_loop

            if next_time is None:
                next_time = 'PAUSED'
            else:
                next_time = next_time.strftime("%I:%M:%S %p")

            if not is_running:
                await interaction.response.send_message(f'Autochecker is not running')
            else:
                await interaction.response.send_message(
                    f'Autochecker is running:\n- Current Loop: {current_loop}\n- Next Iteration: {next_time}')

        elif interaction.user.id != CONFIG.OWNER_DISCORD_ID:
            await interaction.response.send_message('You do not have the permissions to use this command')

        elif command == 'start':
            if is_running:
                await interaction.response.send_message('Autochecker is already running')
                return
            await interaction.response.send_message('Autochecker has restarted')
            log('Autochecker - restart')
            await automatic_announcement_check.start()

        elif command == 'unpause':
            if not is_running:
                await interaction.response.send_message('Autochecker is not running')
                return
            if next_time is None:
                automatic_announcement_check.restart()
                log('Autochecker - on')
                await interaction.response.send_message('Autochecker has been unpaused')
            else:
                await interaction.response.send_message('Autochecker is not paused')

        elif command == 'pause':
            if not is_running or next_time is None:
                await interaction.response.send_message('Autochecker is not running')
                return
            automatic_announcement_check.stop()
            log('Autochecker - off')
            await interaction.response.send_message('Autochecker has been paused')

        else:
            await interaction.response.send_message('Invalid command')

    @bot.tree.command(name="claim_profile", description="Claim your account to get pinged for your own achievements")
    async def claim_profile(interaction: discord.Interaction, index: int):
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

        index -= 1

        tracked[index]['claimed_users'].add(interaction.user.id)
        await interaction.response.send_message(f"You have claimed {tracked[index]['name']}#{tracked[index]['tag']}")
        storage.write(tracked_players, output_channels)

    @bot.tree.command(name="unclaim_profile", description="Unclaim a profile to stop being pinged (Weak)")
    async def unclaim_profile(interaction: discord.Interaction, index: int):
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

        index -= 1

        claimed = tracked[index]['claimed_users']
        if interaction.user.id in claimed:
            claimed.remove(interaction.user.id)
            await interaction.response.send_message(f"You have unclaimed {tracked[index]['name']}#{tracked[index]['tag']}")
            storage.write(tracked_players, output_channels)
        else:
            await interaction.response.send_message(f"You have not claimed {tracked[index]['name']}#{tracked[index]['tag']}")

    @bot.tree.command(name="who_claims", description="See all users who claim a profile")
    async def who_claims(interaction: discord.Interaction, index: int):
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

        index -= 1

        profile = tracked[index]
        msg = f"{profile['name']}#{profile['tag']} is claimed by {
            num_of('user', len(profile['claimed_users']))}{':' if len(profile['claimed_users']) else ''}"
        for user_id in profile['claimed_users']:
            user = await bot.fetch_user(user_id)
            name = user.display_name if user else 'Unknown User'
            msg += f'\n- {name}'
        await interaction.response.send_message(msg)

    @bot.tree.command(name="leaderboard", description="Get the ranked leaderboard of all tracked users")
    async def leaderboard(interaction: discord.Interaction, mode: Literal['Solo/Duo', 'Flex'] = 'Solo/Duo'):
        log_command(interaction)
        ranked_players = events.get_ordered_solo_rankings()

        g_id = interaction.guild_id
        if g_id not in tracked_players:
            await interaction.response.send_message(f'No players are being tracked')
            return
        tracked = tracked_players[g_id]

        embed = embed_generator.leaderboard(mode, ranked_players, tracked)
        await interaction.response.send_message(embed=embed)

    # @bot.tree.command(name="sync", description="Refresh bot commands")
    # async def sync(interaction: discord.Interaction):
    #     log_command(interaction)
    #     if interaction.user.id != CONFIG.OWNER_DISCORD_ID:
    #         await interaction.response.send_message('You do not have the permissions to use this command')
    #     await interaction.response.defer()
    #     await bot.tree.sync(guild=discord.Object(interaction.guild_id))
    #     await interaction.followup.send('Commands Synced')

    def update_remembered_levels():
        for puuid, memory in events.player_memory.items():
            for tracked in tracked_players.values():
                for player in tracked:
                    if player['puuid'] == puuid:
                        player['level'] = memory['level']
        storage.write(tracked_players, output_channels)

    @tasks.loop(seconds=300)  # Repeat every 5 mins
    async def automatic_announcement_check():
        for guild_id, channel_id in output_channels.items():
            if guild_id not in tracked_players:
                continue

            try:
                announcments = await events.check([p['puuid'] for p in tracked_players[guild_id]])
            except Exception:
                log(f'Couldn\'t check announcements for [{guild_id}]', 'ERROR')
                log(traceback.format_exc(), 'ERROR')
                continue

            if len(announcments) == 0:
                continue

            embeds = [e.embed() for e in announcments]
            channel = cast(discord.TextChannel, bot.get_channel(channel_id))
            for i in range(0, ceil(len(embeds) / 10), 10):
                mentions = get_mentions_from_events(
                    announcments[i:i + 10], guild_id)
                await channel.send(mentions, embeds=embeds[i:i + 10])

            update_remembered_levels()

    bot.run(CONFIG.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
