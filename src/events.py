from typing import List, Literal, Union
import asyncio
from riot.api import RiotAPI
from dataclasses import dataclass
from game_info import UserInfo, GameInfo
from logs import log
from utils import flat, num_of


@dataclass
class GameEvent:
    user: UserInfo
    game: GameInfo
    kind: Literal['KDA', 'Lose Streak']

    kda: str = ''
    champ: str = ''

    streak: int = 0


class EventManager():
    BAD_KDA = 1
    HISTORY_COUNT = 20

    riot: RiotAPI
    player_memory: dict[str, object]

    def __init__(self, riot: RiotAPI) -> None:
        self.riot = riot
        self.player_memory = {}

    async def check(self, puuids: List[str], quiet=False):
        if not quiet:
            log('Running event checks...')
        tasks = [self.check_user(puuid) for puuid in puuids]
        events = flat(await asyncio.gather(*tasks))
        if not quiet:
            log(f'Completed event checks ({
                num_of('new announcement', len(events))})')
        return events

    async def check_user(self, puuid: str) -> List[GameEvent]:
        response = await self.riot.get_profile_info(puuid)
        if response.error():
            return []
        user: UserInfo = response.data

        game_ids = (await self.riot.get_matches_ids_by_puuid(puuid, self.HISTORY_COUNT)).data
        memory = self.player_memory.get(puuid)

        if memory is None or memory['last_game'] not in game_ids:
            log(f'Resetting player memory for [{user.summoner_name}]')
            await self.remember_game(puuid, user.id, game_ids[0], game_ids[1:])
            return []

        new_game_ids = game_ids[:game_ids.index(memory['last_game'])]

        new_games = await asyncio.gather(*[self.riot.get_match_info_by_id(gid)
                                           for gid in new_game_ids])

        if new_games:
            log(f'Scanning {num_of('new game', len(new_games))
                            } from [{user.summoner_name}]')

        events = self.find_events_from_games(
            user, new_games, memory['lose_streak'])

        await self.remember_game(puuid, user.id, game_ids[0], game_ids[1:])

        return events

    def find_events_from_games(self, user: UserInfo, games: List[GameInfo], lose_streak: int):
        events = []
        for game in reversed(games):
            info = self.extract_user_match_info(user.id, game)
            if info['kda'] != 'Perfect' and float(info['kda']) < self.BAD_KDA:
                events.append(GameEvent(
                    user,
                    game,
                    kind='KDA',
                    kda=info['kda'],
                    champ=info['champ']
                ))

            if not info['win']:
                lose_streak += 1
                if lose_streak >= 3:
                    events.append(GameEvent(
                        user,
                        game,
                        kind='Lose Streak',
                        champ=info['champ'],
                        streak=lose_streak
                    ))
            else:
                lose_streak = 0

        return events

    def extract_user_match_info(self, user_id: str, game: GameInfo):
        p = [p for p in game.participants if p.id == user_id]
        if p:
            return {
                'win': p[0].team == game.winner,
                'kda': p[0].kda(),
                'champ': p[0].champion_name
            }

    def did_user_win(self, user_id: str, game: GameInfo) -> bool:
        if game is None:
            return True
        p = [p for p in game.participants if p.id == user_id]
        return (p[0].team == game.winner) if p else True

    async def remember_game(self, puuid: str, user_id: str, game_id: str, history: List[str]) -> None:
        match = await self.riot.get_match_info_by_id(game_id)
        lose_streak = 0 if self.did_user_win(user_id, match) else 1

        if lose_streak:
            for prev_game_id in history:
                prev_match = await self.riot.get_match_info_by_id(prev_game_id)
                if self.did_user_win(user_id, prev_match):
                    break
                lose_streak += 1

        self.player_memory[puuid] = {
            'last_game': game_id,
            'last_played': match.start_time,
            'lose_streak': lose_streak
        }

    async def set_memory_to_game(self, puuid: str, game_id: Union[str, None] = None, offset: int = 0) -> bool:
        response = await self.riot.get_profile_info(puuid)
        if response.error():
            return False
        user: UserInfo = response.data

        matches_res = await self.riot.get_matches_ids_by_puuid(puuid, 20)
        if matches_res.error():
            log('Error: ' + matches_res.error(), 'ERROR')
            return False
        game_ids = matches_res.data
        if game_id is not None and game_id not in game_ids:
            return False

        if game_id is None:
            game_id = game_ids[offset]
            index = 1 + offset
        else:
            index = game_ids.index(game_id)
        print(game_id)

        await self.remember_game(puuid, user.id, game_id, game_ids[index:])
        return True


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    riot_client = RiotAPI(os.getenv('RIOT_TOKEN'), 'euw1', 'europe')
    events = EventManager(riot_client)

    user = asyncio.run(riot_client.get_riot_account_puuid('alfais', 'at1'))
    puuid = user.data['puuid']
    print(puuid)
    asyncio.run(events.set_memory_to_game(puuid, offset=2))
    print(asyncio.run(events.check([puuid])))
