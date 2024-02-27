from dataclasses import dataclass
from typing import List


@dataclass
class GameInfo:
    id: int
    start_time: int
    duration: int
    winner: str
    participants: List
    queue_type: str


@dataclass
class PlayerInfo:
    id: int
    summoner_name: str
    kills: int
    deaths: int
    assists: int
    champion_name: str
    champion_id: any  # Not sure what this is supposed to be yet
    gold: int
    damage: int
    creep_score: int
    vision_score: int
    team: int
    multikills: int
    position: int

    def kda(self):
        if self.deaths == 0:
            return "Perfect"
        return str(round((self.kills + self.assists) / self.deaths, 2))


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
