import asyncio
import dataclasses
from typing import List, TypedDict, cast
from events import BaseGameEvent, LowKDAEvent, LoseStreakEvent, RankChangeEvent
from riot import RiotAPI, UserInfo, GameInfo, RanksDict, Rank
from logs import log
from utils import flat, num_of


class Memory(TypedDict):
    last_game: str
    last_played: int
    lose_streak: int
    ranks: RanksDict
    # rank_solo: RankOption
    # rank_flex: RankOption
    # lp_solo: int
    # lp_flex: int
    level: int


class OrderedUserRank(TypedDict):
    puuid: str
    rank: Rank


class EventManager():
    BAD_KDA = 1
    HISTORY_COUNT = 20

    riot: RiotAPI
    player_memory: dict[str, Memory]

    def __init__(self, riot: RiotAPI) -> None:
        self.riot = riot
        self.player_memory = {}

    async def check(self, puuids: List[str], quiet=False):
        if not quiet:
            log('Running event checks...', source='main.events')
        tasks = [self.check_user(puuid) for puuid in puuids]
        events = flat(await asyncio.gather(*tasks))
        if not quiet:
            log(f'Completed event checks ({
                num_of('new announcement', len(events))})', source='main.events')
        return events

    async def check_user(self, puuid: str) -> List[BaseGameEvent]:
        response = await self.riot.get_profile_info(puuid)
        if response.error():
            response.log_error(
                2, 'Couldn\'t get profile from puuid', 'main.events')
            return []
        user: UserInfo = response.data

        game_ids_res = await self.riot.get_matches_ids_by_puuid(puuid, self.HISTORY_COUNT)
        if game_ids_res.data is None:
            game_ids_res.log_error(
                9, "Couldn't get game ids for puuid", 'main.events')
            return []
        game_ids = game_ids_res.data
        memory = self.player_memory.get(puuid)

        if memory is None or memory['last_game'] not in game_ids:
            log(f'Resetting player memory for [{
                user.summoner_name}]', source='main.events')
            await self.remember_history(user, game_ids)
            return []

        new_game_ids = game_ids[:game_ids.index(memory['last_game'])]

        new_games = await asyncio.gather(*[self.riot.get_match_info_by_id(gid)
                                           for gid in new_game_ids])

        new_games = [g for g in new_games if g is not None]

        if new_games:
            log(f'Scanning {num_of('new game', len(new_games))
                            } from [{user.summoner_name}]', source='main.events')

        events = self.find_events_from_games(user, new_games, memory)

        for mode, rank in user.ranks.items():
            if not rank.is_same_as(memory['ranks'][mode]):
                events.append(RankChangeEvent(
                    user, new_games[0],
                    old_rank=memory['ranks'][mode],
                    mode=mode
                ))

        await self.remember_history(user, game_ids)

        return events

    def find_events_from_games(self, user: UserInfo, games: List[GameInfo], memory: Memory):
        events = []
        for game in reversed(games):
            participant = self.match_participant(user.id, game)
            if participant is None:
                log(f"Couldn't find participant matching user id [{user.id}] for [{
                    user.summoner_name}] in game [{game.id}]", 'ERROR', 'main.events')
                continue

            if participant.kda() != 'Perfect' and float(participant.kda()) < self.BAD_KDA:
                events.append(LowKDAEvent(user, game))

            if game.winner == 'Remake':
                continue

            if not participant.team == game.winner:
                memory['lose_streak'] += 1
                if memory['lose_streak'] >= 3:
                    events.append(LoseStreakEvent(
                        user, game, memory['lose_streak']))
            else:
                memory['lose_streak'] = 0

        return events

    def match_participant(self, user_id: str, game: GameInfo):
        p = [p for p in game.participants if p.id == user_id]
        return p[0] if p else None

    def did_user_win(self, user_id: str, game: GameInfo) -> bool:
        if game is None:
            return True
        p = [p for p in game.participants if p.id == user_id]
        return (p[0].team == game.winner) if p else True

    async def remember_history(self, user: UserInfo, history: List[str]) -> None:
        lose_streak = 0
        last_played = 0

        for i, game_id in enumerate(history):
            game = await self.riot.get_match_info_by_id(game_id)
            if game is None:
                log(f"Couldn't get game for id [{
                    game_id}] in history of [{user.summoner_name}]")
                continue

            if i == 0:
                last_played = game.start_time

            if game.winner == 'Remake':
                continue
            if self.did_user_win(user.id, game):
                break
            lose_streak += 1

        self.player_memory[user.puuid] = {
            'last_game': history[0],
            'last_played': last_played,
            'lose_streak': lose_streak,
            'ranks': {
                'Solo/Duo': dataclasses.replace(user.ranks['Solo/Duo']),
                'Flex': dataclasses.replace(user.ranks['Flex'])
            },
            'level': user.level
        }

    def get_ordered_solo_rankings(self) -> List[OrderedUserRank]:
        ranked_players = [{'puuid': puuid, 'rank': m['ranks']['Solo/Duo']}
                          for puuid, m in self.player_memory.items()
                          if m['ranks']['Solo/Duo'].division != 'UNRANKED']
        ranked_players = cast(List[OrderedUserRank], ranked_players)
        ranked_players.sort(key=lambda x: x['rank'].id(), reverse=True)
        return ranked_players

    async def set_memory_to_game(self, puuid: str, offset: int = 0) -> bool:
        response = await self.riot.get_profile_info(puuid)
        if response.error():
            response.log_error(
                3, 'Couldn\'t get profile from puuid', 'main.events')
            return False
        user: UserInfo = response.data

        matches_res = await self.riot.get_matches_ids_by_puuid(puuid, 20)
        if matches_res.error():
            response.log_error(
                4, 'Couldn\'t get game ids for puuid', 'main.events')
            return False

        await self.remember_history(user, matches_res.data[offset:])
        return True


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    riot_client = RiotAPI(os.getenv('RIOT_TOKEN', ''), 'euw1', 'europe', 2)
    events = EventManager(riot_client)

    user = asyncio.run(
        riot_client.get_riot_account_puuid('im not from here', '9969'))
    if user.error():
        user.log_error(0)
        exit(1)
    puuid = user.data['puuid']
    print(puuid)
    asyncio.run(events.set_memory_to_game(puuid, offset=1))
    print([e for e in asyncio.run(events.check([puuid]))])
