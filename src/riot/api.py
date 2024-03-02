import aiohttp
from typing import List
from asyncio import Semaphore
from game_info import GameInfo, PlayerInfo, UserInfo, UserChamp
from utils import cache_with_timeout
from .responses import APIResponse, APILeagueEntry, APIRiotAccount, APISummoner, APIMatch


class RiotAPI:
    queueTypes = {
        400: "Draft",
        420: "Solo/Duo",
        430: "Blind",
        440: "Flex",
        450: "ARAM",
        700: "Clash",
    }
    queueWeight = {
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

        self.sem = Semaphore(5)

    @classmethod
    def is_rank_growth(cls, rank1: str, rank2: str) -> bool:
        if rank1 == 'UNRANKED':
            return True
        elif rank2 == 'UNRANKED':
            return False

        r1, t1 = rank1.split(' ')
        r2, t2 = rank2.split(' ')

        wdiff = cls.queueWeight.get(r1, 0) - cls.queueWeight.get(r2, 0)
        if wdiff > 0:
            return False
        elif wdiff < 0:
            return True

        tiers = ['I', 'II', 'III', 'IV']
        return tiers.index(t1.upper()) > tiers.index(t2.upper())

    async def api(self, url: str, params: dict = {}, universal=False) -> APIResponse:
        base_url = self.base_url_universal if universal else self.base_url
        params["api_key"] = self.api_key
        async with aiohttp.ClientSession() as session:
            async with self.sem, session.get(base_url + url, params=params) as response:
                if response.status == 200:
                    return APIResponse(data=await response.json())
                else:
                    r = APIResponse(status=response.status)
                    if r.error() == 'unknown':
                        raise Exception(str(response))
                    return r

    @cache_with_timeout(600)
    async def get_riot_account_puuid(self, name: str, tag: str) -> APIResponse[APIRiotAccount]:
        url = f"/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        return await self.api(url, universal=True)

    @cache_with_timeout(270)
    async def get_summoner_by_puuid(self, puuid: str) -> APIResponse[APISummoner]:
        return await self.api(f"/lol/summoner/v4/summoners/by-puuid/{puuid}")

    @cache_with_timeout()
    async def get_matches_ids_by_puuid(self, puuid: str, count: int = 20, start: int = 0) -> APIResponse[List[str]]:
        url = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"count": count, "start": start}
        return await self.api(url, params, universal=True)

    @cache_with_timeout(300)
    async def get_raw_match_info_by_id(self, match_id: str) -> APIResponse[APIMatch]:
        return await self.api(f"/lol/match/v5/matches/{match_id}", universal=True)

    @cache_with_timeout()
    async def get_ranked_info(self, user_id: str):
        data: APIResponse[List[APILeagueEntry]] = await self.api(f"/lol/league/v4/entries/by-summoner/{user_id}")

        ranks = []
        for rankData in data.data:
            if "rank" not in rankData:
                continue
            queue = rankData["queueType"]
            tier = rankData["tier"]
            rank = rankData["rank"]
            lp = rankData["leaguePoints"]
            wins = rankData["wins"]
            losses = rankData["losses"]
            rankArray = [queue, tier, rank, lp, wins, losses]
            ranks.append(rankArray)
        return ranks

    @cache_with_timeout()
    async def get_mastery_info(self, puuid: str) -> List[UserChamp]:
        data = await self.api(f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}")
        return [
            UserChamp(c["championId"], c["championLevel"], points=c["championPoints"],
                      last_play=c["lastPlayTime"],    chest=c["chestGranted"])
            for c in data.data
        ]

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
        summoner = await self.get_summoner_by_puuid(puuid)
        if summoner.error() is not None:
            summoner.log_error(8, 'Couldn\'t get summoner from puuid')
            return summoner

        user = UserInfo(
            id=summoner.data["id"],
            puuid=puuid,
            summoner_name=summoner.data["name"],
            level=summoner.data["summonerLevel"],
            icon=summoner.data["profileIconId"],
        )

        for rank in await self.get_ranked_info(user.id):
            if rank[0] == "RANKED_SOLO_5x5":
                user.rank_solo = f"{rank[1]} {rank[2]}"
                user.lp_solo = rank[3]
                user.wins_solo = rank[4]
                user.losses_solo = rank[5]
            elif rank[0] == "RANKED_FLEX_SR":
                user.rank_flex = f"{rank[1]} {rank[2]}"
                user.lp_flex = rank[3]
                user.wins_flex = rank[4]
                user.losses_flex = rank[5]
            if (
                self.queueWeight[user.max_division.upper()]
                < self.queueWeight[rank[1].upper()]
            ):
                user.max_division = rank[1].upper()

        champions = await self.get_mastery_info(puuid)

        user.top_champs = champions[:3]
        user.total_mastery = sum(map(lambda c: c.level, champions))
        user.total_points = sum(map(lambda c: c.points, champions))

        return APIResponse(data=user)
