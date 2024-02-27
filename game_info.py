from dataclasses import dataclass
from typing import List, Literal
from datetime import datetime
from logs import r_pad


@dataclass
class PlayerInfo:
    id: str
    summoner_name: str
    kills: int
    deaths: int
    assists: int
    champion_name: str
    champion_id: int
    gold: int
    damage: int
    creep_score: int
    vision_score: int
    team: Literal['Red', 'Blue']
    multikills: List[int]
    position: Literal['UTILITY', 'BOTTOM', 'MIDDLE', 'JUNGLE', 'TOP']

    def kda(self) -> str:
        if self.deaths == 0:
            return "Perfect"
        return str(round((self.kills + self.assists) / self.deaths, 2))


@dataclass
class GameInfo:
    id: int
    start_time: int
    duration: int
    winner: Literal['Red', 'Blue']
    participants: List[PlayerInfo]
    queue_type: Literal['Draft', 'Solo/Duo',
                        'Blind', 'Flex', 'ARAM', 'Clash', 'Other']

    def __str__(self) -> str:
        output = datetime.fromtimestamp(self.start_time / 1000)\
            .strftime("%a, %d %b %Y %I:%M%p")

        output += f' ({round(self.duration / 60, 1)} mins)'
        output += f' - {"🔴" if self.winner == "Red" else "🔵"} Wins!'

        red_team = [f'{p.summoner_name} ({p.champion_name})'
                    for p in self.participants if p.team == 'Red']
        blue_team = [f'{p.summoner_name} ({p.champion_name})'
                     for p in self.participants if p.team == 'Blue']

        max_len = max(map(len, red_team))
        for r, b in zip(red_team, blue_team):
            output += f'\n🔴 {r_pad(r, max_len)}   🔵 {b}'

        return output


@dataclass
class UserChamp:
    id: int
    level: int
    points: int
    last_play: int
    chest: bool


@dataclass
class UserInfo:
    id: str
    summoner_name: str
    level: int
    icon: int
    rank_solo: str
    rank_flex: str
    lp_solo: int
    lp_flex: int
    wins_solo: int
    losses_solo: int
    wins_flex: int
    losses_flex: int
    max_division: str
    top_champs: List[UserChamp]
    total_points: int
    total_mastery: int
