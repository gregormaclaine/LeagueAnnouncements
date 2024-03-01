from dataclasses import dataclass, field
from typing import List, Literal, TypedDict, Optional
from datetime import datetime
from utils import r_pad


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

    def score(self) -> str:
        return f'{self.kills}/{self.deaths}/{self.assists}'

    def kda(self) -> str:
        if self.deaths == 0:
            return "Perfect"
        return str(round((self.kills + self.assists) / self.deaths, 2))


@dataclass
class GameInfo:
    id: int
    start_time: int
    duration: int
    winner: Literal['Red', 'Blue', 'Remake']
    participants: List[PlayerInfo]
    queue_type: Literal['Draft', 'Solo/Duo',
                        'Blind', 'Flex', 'ARAM', 'Clash', 'Other']

    def get_player(self, id: str):
        p = [p for p in self.participants if p.id == id]
        return p[0] if len(p) else None

    def __str__(self) -> str:
        output = datetime.fromtimestamp(self.start_time / 1000)\
            .strftime("%a, %d %b %Y %I:%M%p")

        output += f' ({round(self.duration / 60, 1)} mins)'

        emoji = {
            "Red": "🔴",
            "Blue": "🔵",
            "Remake": "⚪"
        }[self.winner]
        output += f' - {emoji} Wins!'

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


type RankOption = Literal["UNRANKED", "IRON", "BRONZE", "SILVER", "GOLD",
                          "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]


@dataclass
class UserInfo:
    id: str = ''
    puuid: str = ''
    summoner_name: str = 'Unknown User'
    level: int = 0
    icon: int = 1
    rank_solo: RankOption = 'UNRANKED'
    rank_flex: RankOption = 'UNRANKED'
    lp_solo: int = 0
    lp_flex: int = 0
    wins_solo: int = 0
    losses_solo: int = 0
    wins_flex: int = 0
    losses_flex: int = 0
    max_division: RankOption = "UNRANKED"
    top_champs: List[UserChamp] = field(default_factory=list)
    total_points: int = 0
    total_mastery: int = 0

    def total_solo_games(self):
        return self.wins_solo + self.losses_solo

    def total_flex_games(self):
        return self.wins_flex + self.losses_flex

    def solo_winrate(self):
        rate = self.wins_solo / self.total_solo_games()
        return f'{rate * 100:.2f}%'

    def flex_winrate(self):
        rate = self.wins_flex / self.total_flex_games()
        return f'{rate * 100:.2f}%'

    def solo_info(self):
        s = ''
        if self.rank_solo != 'UNRANKED':
            s += str(self.lp_solo) + ' LP, '
        s += f'{self.total_solo_games()} games'
        if self.total_solo_games() > 0:
            s += f', {self.solo_winrate()} WR'
        return s

    def flex_info(self):
        s = ''
        if self.rank_flex != 'UNRANKED':
            s += str(self.lp_flex) + ' LP, '
        s += f'{self.total_flex_games()} games'
        if self.total_flex_games() > 0:
            s += f', {self.flex_winrate()} WR'
        return s


class TrackPlayer(TypedDict):
    puuid: str
    name: str
    tag: str
    level: int
    claimed_users: set[int]
