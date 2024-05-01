import aiohttp
from typing import List, Literal, cast, Optional
from asyncio import Semaphore, sleep
from datetime import datetime
from utils import cache_with_timeout
from .structs import GameInfo, PlayerInfo, Rank, RankOption, QueueType, RanksDict, UserInfo, UserChamp, TierOption
from .responses import APIResponse, APILeagueEntry, APIRiotAccount, APISummoner, APIMatch, APISummonerName


class RiotAPI:
    queueTypes: dict[int, QueueType] = {
        400: "Draft",
        420: "Solo/Duo",
        430: "Blind",
        440: "Flex",
        450: "ARAM",
        700: "Clash",
    }
    queueWeight: dict[RankOption, int] = {
        "UNRANKED": -1,
        "IRON": 0,
        "BRONZE": 1,
        "SILVER": 2,
        "GOLD": 3,
        "PLATINUM": 4,
        "EMERALD": 5,
        "DIAMOND": 6,
        "MASTER": 7,
        "GRANDMASTER": 8,
        "CHALLENGER": 9,
    }

    def __init__(self, api_key: str, server: str, region: str, api_threads: int):
        self.api_key = api_key
        self.base_url = f"https://{server}.api.riotgames.com"
        self.base_url_universal = f"https://{region}.api.riotgames.com"

        # Rate-limiting prevention
        self.sem = Semaphore(api_threads)
        self.timeout_start = None
        self.active_calls = 0
        self.completed_calls = 0
        self.waiting_calls = 0

        self.max_calls = 100
        self.time_window = 121

    def time_till_rate_limit_resets(self):
        return self.time_window - (datetime.now() - self.timeout_start).seconds

    async def api(self, url: str, params: dict = {}, universal=False) -> APIResponse:
        while self.timeout_start and self.active_calls + self.completed_calls >= self.max_calls:
            wait = self.time_till_rate_limit_resets()
            if wait > 0:
                self.waiting_calls += 1
                await sleep(wait)
                self.waiting_calls -= 1
            else:
                self.completed_calls = 0

        self.active_calls += 1

        base_url = self.base_url_universal if universal else self.base_url
        params["api_key"] = self.api_key

        async with aiohttp.ClientSession() as session:
            async with self.sem, session.get(base_url + url, params=params) as response:
                resobj = APIResponse(
                    status=response.status,
                    data=(await response.json()) if response.content_type == 'application/json' else None,
                    rate_limit_info=(
                        response.headers.get('X-App-Rate-Limit-Count'), response.headers.get('X-App-Rate-Limit'))
                )

                current = resobj.rate_limit_count()
                self.active_calls -= 1
                self.completed_calls += 1

                # Save the time if this is the first call in the 2 minute window
                if current == 1 or self.timeout_start is None:
                    self.timeout_start = datetime.now()

                # Accounts for when the rate limit didn't start from 0 (When restarting bot)
                elif current > self.completed_calls + self.active_calls:
                    self.completed_calls = current

                # Only prints once when the final call of the window completes
                elif current == self.max_calls:
                    secs = self.time_till_rate_limit_resets()
                    print(
                        f'Hit rate-limit ceiling: {self.waiting_calls} calls waiting {secs} seconds before restarting...')

                if resobj.error() == 'unknown':
                    raise Exception(str(response))

                return resobj

    @cache_with_timeout(600)
    async def get_riot_account_puuid(self, name: str, tag: str) -> APIResponse[APIRiotAccount]:
        url = f"/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        return await self.api(url, universal=True)

    @cache_with_timeout(12 * 60 * 60)
    async def get_summoner_name_from_puuid(self, puuid: str) -> APIResponse[APISummonerName]:
        return await self.api('/riot/account/v1/accounts/by-puuid/' + puuid, universal=True)

    @cache_with_timeout(270)
    async def get_summoner_by_puuid(self, puuid: str) -> APIResponse[APISummoner]:
        return await self.api(f"/lol/summoner/v4/summoners/by-puuid/{puuid}")

    @cache_with_timeout()
    async def get_matches_ids_by_puuid(self, puuid: str, count: int = 20, start: int = 0, type: Optional[Literal['ranked', 'normal', 'tourney', 'tutorial']] = None) -> APIResponse[List[str]]:
        url = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"count": count, "start": start}
        if type:
            params['type'] = type
        return await self.api(url, params, universal=True)

    @cache_with_timeout(300)
    async def get_raw_match_info_by_id(self, match_id: str) -> APIResponse[APIMatch]:
        return await self.api(f"/lol/match/v5/matches/{match_id}", universal=True)

    @cache_with_timeout()
    async def get_ranked_info(self, user_id: str) -> APIResponse[dict[Literal['Solo/Duo', 'Flex'], Rank]]:
        data: APIResponse[List[APILeagueEntry]] = await self.api(f"/lol/league/v4/entries/by-summoner/{user_id}")
        if data.error():
            return cast(APIResponse[dict[Literal['Solo/Duo', 'Flex'], Rank]], data)

        ranks: RanksDict = {}

        for rankData in data.data:
            if rankData['queueType'] == 'RANKED_SOLO_5x5':
                ranks['Solo/Duo'] = Rank.from_data(rankData)
            elif rankData['queueType'] == 'RANKED_FLEX_SR':
                ranks['Flex'] = Rank.from_data(rankData)

        if 'Solo/Duo' not in ranks:
            ranks['Solo/Duo'] = Rank.unranked()

        if 'Flex' not in ranks:
            ranks['Flex'] = Rank.unranked()

        return APIResponse(200, ranks)

    @cache_with_timeout()
    async def get_mastery_info(self, puuid: str) -> APIResponse[List[UserChamp]]:
        data = await self.api(f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}")
        if data.error():
            return data

        return APIResponse(200, [
            UserChamp(c["championId"], c["championLevel"], points=c["championPoints"],
                      last_play=c["lastPlayTime"],    chest=c["chestGranted"])
            for c in data.data
        ])

    async def get_match_info_by_id(self, match_id: str):
        data_res = await self.get_raw_match_info_by_id(match_id)
        if data_res.error() is not None:
            data_res.log_error(7, 'Couldn\'t get match info')
            return None

        raw_data = data_res.data
        start_time = raw_data["info"]["gameStartTimestamp"]
        game_duration = raw_data["info"]["gameDuration"]
        queue_type = self.queueTypes.get(raw_data["info"]["queueId"], 'Other')
        winner = "Blue"
        participants = []
        for participant in raw_data["info"]["participants"]:
            team = "Red"
            if participant["teamId"] == 100:
                team = "Blue"
            if participant["win"] and team == "Red":
                winner = "Red"

            player_info = PlayerInfo(
                id=participant["summonerId"],
                summoner_name=participant["summonerName"],
                kills=participant["kills"],
                deaths=participant["deaths"],
                assists=participant["assists"],
                champion_name=participant["championName"],
                champion_id=participant["championId"],
                gold=participant["goldEarned"],
                damage=participant["totalDamageDealtToChampions"],
                creep_score=(participant["totalMinionsKilled"] +
                             participant["neutralMinionsKilled"]),
                vision_score=participant["visionScore"],
                team='Blue' if participant["teamId"] == 100 else 'Red',
                multikills=[
                    participant["doubleKills"],
                    participant["tripleKills"],
                    participant["quadraKills"],
                    participant["pentaKills"]
                ],
                position=participant["individualPosition"]
            )
            participants.append(player_info)

        if game_duration < 300:
            winner = 'Remake'

        return GameInfo(match_id, start_time, game_duration,
                        winner, participants, queue_type)

    async def get_profile_info(self, puuid: str) -> APIResponse[UserInfo]:
        summoner_name = await self.get_summoner_name_from_puuid(puuid)
        if summoner_name.error() is not None:
            summoner_name.log_error(
                15, 'Couldn\'t get summoner name info from puuid')
            return cast(APIResponse[UserInfo], summoner_name)

        summoner = await self.get_summoner_by_puuid(puuid)
        if summoner.error() is not None:
            summoner.log_error(8, 'Couldn\'t get summoner from puuid')
            return cast(APIResponse[UserInfo], summoner)

        try:
            user = UserInfo(
                id=summoner.data["id"],
                puuid=puuid,
                summoner_name=summoner_name.data['gameName'],
                summoner_tag=summoner_name.data['tagLine'],
                level=summoner.data["summonerLevel"],
                icon=summoner.data["profileIconId"]
            )
        except KeyError:
            summoner.log_error(
                14, 'Couldn\'t read summoner data: ' + str(summoner.data))
            return cast(APIResponse[UserInfo], summoner)

        ranks = await self.get_ranked_info(user.id)
        if ranks.error():
            ranks.log_error(
                12, f'Couldn\'t get summoner ranked info from user id [{user.id}]')
            return cast(APIResponse[UserInfo], ranks)
        user.ranks = ranks.data

        champions = await self.get_mastery_info(puuid)
        if champions.error():
            champions.log_error(
                13, f'Couldn\'t get summoner mastery from puuid [{puuid}]')
            return cast(APIResponse[UserInfo], champions)

        user.top_champs = champions.data[:3]
        user.total_mastery = sum(map(lambda c: c.level, champions.data))
        user.total_points = sum(map(lambda c: c.points, champions.data))

        return APIResponse(data=user)
