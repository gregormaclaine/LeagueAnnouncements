import aiohttp
from typing import List
from game_info import GameInfo, PlayerInfo, UserInfo, UserChamp


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
        self.base_url = f"https://{server}.api.riotgames.com/"
        self.base_url_universal = f"https://{region}.api.riotgames.com/"

    async def get_riot_account_puuid(self, gameName: str, tagLine: str):
        url = f"{self.base_url_universal}riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
        params = {"api_key": self.api_key}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                if response.status == 200:
                    return data["puuid"]
                return None

    async def get_summoner_by_puuid(self, puuid: str):
        url = f"{self.base_url}lol/summoner/v4/summoners/by-puuid/{puuid}"
        params = {"api_key": self.api_key}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                if response.status == 200:
                    data["status_code"] = response.status
                    data["message"] = "Summoner found"
                    return data
                return data["status"]

    async def get_matches_ids_by_puuid(self, puuid: str, count: int = 20, start: int = 0) -> List[str]:
        url = f"{self.base_url_universal}lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"api_key": self.api_key, "count": count, "start": start}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                if response.status == 200:
                    return data
                return []

    async def get_raw_match_info_by_id(self, match_id: str):
        url = f"{self.base_url_universal}lol/match/v5/matches/{match_id}"
        params = {"api_key": self.api_key}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                if response.status == 200:
                    data["status_code"] = response.status
                    data["message"] = "Match found"
                    return data
                return data["status"]

    async def get_recent_matches_ids(self, puuid: str, count: int = 20):
        summoner_data = await self.get_summoner_by_puuid(puuid)
        if summoner_data["status_code"] != 200:
            return [[], summoner_data]
        summoner_puuid = summoner_data["puuid"]
        return [
            await self.get_matches_ids_by_puuid(summoner_puuid, count=count),
            summoner_data,
        ]

    async def get_match_info_by_id(self, match_id: str):
        raw_data = await self.get_raw_match_info_by_id(match_id)
        if raw_data["status_code"] != 200:
            print('Error: Couldn\'t get match info:', raw_data)
            return None
        start_time = raw_data["info"]["gameStartTimestamp"]
        game_duration = raw_data["info"]["gameDuration"]
        queueId = raw_data["info"]["queueId"]
        queue_type = "Other"
        if queueId in self.queueTypes:
            queue_type = self.queueTypes[queueId]
        winner = "Blue"
        participants = []
        for participant in raw_data["info"]["participants"]:
            id = participant["summonerId"]
            summoner_name = participant["summonerName"]
            kills = participant["kills"]
            deaths = participant["deaths"]
            assists = participant["assists"]
            champion_name = participant["championName"]
            champion_id = participant["championId"]
            gold_earned = participant["goldEarned"]
            damage = participant["totalDamageDealtToChampions"]
            creep_score = (
                participant["totalMinionsKilled"] +
                participant["neutralMinionsKilled"]
            )
            vision_score = participant["visionScore"]
            team = "Red"
            if participant["teamId"] == 100:
                team = "Blue"
            if participant["win"] and team == "Red":
                winner = "Red"
            multikills = [
                participant["doubleKills"],
                participant["tripleKills"],
                participant["quadraKills"],
                participant["pentaKills"],
            ]
            position = participant["individualPosition"]
            player_info = PlayerInfo(
                id,
                summoner_name,
                kills,
                deaths,
                assists,
                champion_name,
                champion_id,
                gold_earned,
                damage,
                creep_score,
                vision_score,
                team,
                multikills,
                position,
            )
            participants.append(player_info)
        game_info = GameInfo(
            id, start_time, game_duration, winner, participants, queue_type
        )
        return game_info

    async def get_recent_matches_infos(self, puuid: str, count: int = 20):
        matches_infos = []
        data = await self.get_recent_matches_ids(puuid, count)
        for match_id in data[0]:
            match_info = await self.get_match_info_by_id(match_id)
            if match_info is not None:
                matches_infos.append(match_info)
        return [matches_infos, data[1]]

    async def get_recent_match_info(self, puuid: str, id: int = 0):
        match_data = await self.get_recent_matches_ids(puuid, id + 1)
        if len(match_data[0]) > id:
            return await self.get_match_info_by_id(match_data[0][id])
        return None

    async def get_ranked_info(self, user_id: str):
        url = f"{self.base_url}lol/league/v4/entries/by-summoner/{user_id}"
        params = {"api_key": self.api_key}
        ranks = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                for rankData in data:
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

    async def get_mastery_info(self, puuid: str) -> List[UserChamp]:
        url = f"{self.base_url}lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        params = {"api_key": self.api_key}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                return [
                    UserChamp(c["championId"], c["championLevel"], points=c["championPoints"],
                              last_play=c["lastPlayTime"],    chest=c["chestGranted"])
                    for c in await response.json()
                ]

    async def get_profile_info(self, puuid: str):
        summoner = await self.get_summoner_by_puuid(puuid)
        if summoner["status_code"] != 200:
            return {"status_code": 404, "message": "Summoner not found"}

        id = summoner["id"]
        summoner_name = summoner["name"]
        level = summoner["summonerLevel"]
        icon = summoner["profileIconId"]
        ranks = await self.get_ranked_info(id)
        rank_solo = "UNRANKED"
        rank_flex = "UNRANKED"
        lp_solo = 0
        lp_flex = 0
        wins_solo = 0
        losses_solo = 0
        wins_flex = 0
        losses_flex = 0
        max_division = "UNRANKED"
        for rank in ranks:
            if rank[0] == "RANKED_SOLO_5x5":
                rank_solo = f"{rank[1]} {rank[2]}"
                lp_solo = rank[3]
                wins_solo = rank[4]
                losses_solo = rank[5]
            elif rank[0] == "RANKED_FLEX_SR":
                rank_flex = f"{rank[1]} {rank[2]}"
                lp_flex = rank[3]
                wins_flex = rank[4]
                losses_flex = rank[5]
            if (
                self.queueWeight[max_division.upper()]
                < self.queueWeight[rank[1].upper()]
            ):
                max_division = rank[1].upper()

        champions = await self.get_mastery_info(puuid)

        user = UserInfo(
            id,
            summoner_name,
            level,
            icon,
            rank_solo,
            rank_flex,
            lp_solo,
            lp_flex,
            wins_solo,
            losses_solo,
            wins_flex,
            losses_flex,
            max_division,
            top_champs=champions[:3],
            total_mastery=sum(map(lambda c: c.level, champions)),
            total_points=sum(map(lambda c: c.points, champions)),
        )
        return {"status_code": 200, "user": user}
