import aiohttp
import time
from typing import List, Literal, cast, Optional
from utils import cache_with_timeout
from logs import log
from config import IS_DEV
from .structs import GameInfo, PlayerInfo, Rank, RankOption, QueueType, RanksDict, UserInfo, UserChamp
from .responses import APIResponse, APILeagueEntry, APIRiotAccount, APISummoner, APIMatch, APISummonerName, APIChampionMastery
from .rate_limiting import handle_rate_limit


def _fmt_endpoint(url: str) -> str:
    parts = url.split('/')
    return '/'.join(p[:6] + '...' if len(p) > 30 else p for p in parts)


def _fmt_rate_limit(info: Optional[tuple[str, str]]) -> str:
    if info is None:
        return ''
    counts = [p.split(':')[0] for p in info[0].split(',')]
    limits = [p.split(':')[0] for p in info[1].split(',')]
    pairs = sorted(zip(counts, limits), key=lambda p: int(p[1]))
    return '  [' + ' | '.join(f'{c}/{l}' for c, l in pairs) + ']'


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

    def __init__(self, api_key: str, server: str, region: str):
        self.api_key = api_key
        self.base_url = f"https://{server}.api.riotgames.com"
        self.base_url_universal = f"https://{region}.api.riotgames.com"

    @handle_rate_limit(max_calls=100, time_window=121, header_order=1)
    # \/ The actual limit is 20/s, but we want to stay a bit under it to avoid triggering the 5s backoff
    @handle_rate_limit(max_calls=16, time_window=1, header_order=0)
    async def api(self, url: str, params: dict = {}, universal=False, has_silent_404s: bool = False) -> APIResponse:
        base_url = self.base_url_universal if universal else self.base_url
        params["api_key"] = self.api_key

        start = time.perf_counter()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url + url, params=params) as response:
                    resobj = APIResponse(
                        status=response.status,
                        data=(await response.json()) if response.content_type == 'application/json' else None,
                        rate_limit_count=response.headers.get(
                            'X-App-Rate-Limit-Count'),
                        rate_limit=response.headers.get('X-App-Rate-Limit')
                    )
                    response_repr = str(response)
        except aiohttp.ClientConnectionError:
            return APIResponse(499)

        if has_silent_404s and resobj.status == 400:
            # Some endpoints (e.g. /lol/summoner/v4/summoners/by-puuid) return 400 instead of 404 when the item isn't found, so we have to account for that
            resobj.status = 404

        if resobj.error() == 'unknown':
            raise Exception(response_repr)

        if True:  # Can be toggled for more concise logging when not debugging
            elapsed_ms = (time.perf_counter() - start) * 1000
            log(f'{_fmt_endpoint(url)}  {resobj.status}  ({elapsed_ms:.0f}ms){_fmt_rate_limit(resobj.rate_limit_info)}', 'API', 'riot.api')

        return resobj

    @cache_with_timeout(600)
    async def get_riot_account_puuid(self, name: str, tag: str) -> APIResponse[APIRiotAccount]:
        url = f"/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        return await self.api(url, universal=True, has_silent_404s=True)

    @cache_with_timeout(12 * 60 * 60)
    async def get_summoner_name_from_puuid(self, puuid: str) -> APIResponse[APISummonerName]:
        return await self.api('/riot/account/v1/accounts/by-puuid/' + puuid, universal=True, has_silent_404s=True)

    async def _get_summoner_name_raw(self, puuid: str) -> APIResponse[APISummonerName]:
        return await self.api('/riot/account/v1/accounts/by-puuid/' + puuid, universal=True, has_silent_404s=True)

    @cache_with_timeout(270)
    async def get_summoner_by_puuid(self, puuid: str) -> APIResponse[APISummoner]:
        return await self.api(f"/lol/summoner/v4/summoners/by-puuid/{puuid}")

    @cache_with_timeout()
    async def get_matches_ids_by_puuid(self, puuid: str, count: int = 20, start: int = 0, type: Optional[Literal['ranked', 'normal', 'tourney', 'tutorial']] = None) -> APIResponse[List[str]]:
        url = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params: dict[str, str | int] = {"count": count, "start": start}
        if type:
            params['type'] = type
        return await self.api(url, params, universal=True)

    @cache_with_timeout(300)
    async def get_raw_match_info_by_id(self, match_id: str) -> APIResponse[APIMatch]:
        return await self.api(f"/lol/match/v5/matches/{match_id}", universal=True)

    @cache_with_timeout()
    async def get_ranked_info(self, puuid: str) -> APIResponse[dict[Literal['Solo/Duo', 'Flex'], Rank]]:
        data: APIResponse[List[APILeagueEntry]] = await self.api(f"/lol/league/v4/entries/by-puuid/{puuid}")
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
        data: APIResponse[List[APIChampionMastery]] = await self.api(f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}")
        if data.error():
            return cast(APIResponse[List[UserChamp]], data)

        return APIResponse(200, [
            UserChamp(c['championId'],
                      c['championLevel'],
                      points=c['championPoints'],
                      last_play=c['lastPlayTime'])
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
                puuid=participant["puuid"],
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

        if summoner_name.error() == 'not-found':
            for _ in range(2):
                summoner_name = await self._get_summoner_name_raw(puuid)
                if summoner_name.error() != 'not-found':
                    break

        if summoner_name.error() is not None:
            summoner_name.log_error(
                15, f'Couldn\'t get summoner name info from puuid [{puuid}]: ' + str(summoner_name.data))
            return cast(APIResponse[UserInfo], summoner_name)

        summoner = await self.get_summoner_by_puuid(puuid)
        if summoner.error() is not None:
            summoner.log_error(8, 'Couldn\'t get summoner from puuid')
            return cast(APIResponse[UserInfo], summoner)

        try:
            user = UserInfo(
                puuid=puuid,
                summoner_name=summoner_name.data['gameName'],
                summoner_tag=summoner_name.data['tagLine'],
                level=summoner.data["summonerLevel"],
                icon=summoner.data["profileIconId"]
            )
        except KeyError:
            print(summoner_name.data)
            summoner.log_error(
                14, 'Couldn\'t read summoner data: ' + str(summoner.data))
            return cast(APIResponse[UserInfo], summoner)

        ranks = await self.get_ranked_info(puuid)
        if ranks.error():
            ranks.log_error(
                12, f'Couldn\'t get summoner ranked info from user [{user.summoner_name}#{user.summoner_tag}]')
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
