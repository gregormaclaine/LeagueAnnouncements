from .api import RiotAPI
from typing import List, TypedDict, Literal
from dataclasses import dataclass
from asyncio import gather
from utils import flat


class ChampAndResult(TypedDict):
    champion_id: int
    result: Literal['win', 'loss', 'remake']


@dataclass
class UserChampionInfo:
    puuid: str
    champion_id: int
    wins: int
    losses: int

    def winrate(self) -> float:
        return self.wins / (self.wins + self.losses)

    def games(self) -> int:
        return self.wins + self.losses


class RiotComputer:
    def __init__(self, api: RiotAPI) -> None:
        self.api = api

    async def calculate_champ_breakdown(self, puuids: List[str], min_games=10) -> List[UserChampionInfo]:
        tasks = [self.calculate_champ_breakdown_for_puuid(puuid, min_games)
                 for puuid in puuids]
        champs = flat(await gather(*tasks))
        champs.sort(key=lambda x: x.winrate(), reverse=True)
        return champs

    async def calculate_champ_breakdown_for_puuid(self, puuid: str, min_games=10) -> UserChampionInfo:
        games = await self.get_all_games_for_puuid(puuid)
        print(f'Collecting {len(games)} games for puuid<{puuid[:10]}...>')
        tasks = [self.get_champ_and_result_from_game(
            puuid, game_id) for game_id in games]
        selections = await gather(*tasks)

        champion_infos = {}
        for result in selections:
            if result is None:
                continue

            champ = result['champion_id']
            if info := champion_infos.get(champ):
                if result['result'] == 'win':
                    info.wins += 1
                elif result['result'] == 'loss':
                    info.losses += 1
            else:
                champion_infos[champ] = UserChampionInfo(
                    puuid, champ,
                    1 if result['result'] == 'win' else 0,
                    1 if result['result'] == 'loss' else 0
                )

        return [c for c in champion_infos.values() if c.games() >= min_games]

    async def get_all_games_for_puuid(self, puuid: str, max_number: int = 1000) -> List[str]:
        games = []
        for i in range(0, max_number, 100):
            num = min(100, max_number - i)

            game_window_res = await self.api.get_matches_ids_by_puuid(puuid, num, i, 'ranked')
            if err := game_window_res.error():
                raise Exception(err)

            new_games = game_window_res.data
            games.extend(new_games)
            if len(new_games) < 100:
                break

        return games

    async def get_champ_and_result_from_game(self, puuid: str, game_id: str) -> ChampAndResult:
        match_res = await self.api.get_raw_match_info_by_id(game_id)
        if err := match_res.error():
            print(err)
            return None
        game = match_res.data
        participants = [p for p in game['info']
                        ['participants'] if p['puuid'] == puuid]

        if len(participants) == 0:
            print(f'Error: Couldn\'t access participant of puuid {
                  puuid} in game {game_id}')
            return None

        participant = participants[0]

        if game['info']['gameDuration'] < 300:
            result = 'remake'
        elif participant['win']:
            result = 'win'
        else:
            result = 'loss'

        return {
            'champion_id': participant['championId'],
            'result': result
        }
