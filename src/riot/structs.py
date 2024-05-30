from datetime import datetime
from dataclasses import dataclass, field, replace
from typing import List, Literal, Optional, Self, cast
from .responses import APILeagueEntry
from utils import r_pad


type QueueType = Literal['Draft', 'Solo/Duo',
                         'Blind', 'Flex', 'ARAM', 'Clash', 'Other']


type RankOption = Literal['UNRANKED', 'IRON', 'BRONZE', 'SILVER', 'GOLD',
                          'PLATINUM', 'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER']

type TierOption = Literal['I', 'II', 'III', 'IV']

type RanksDict = dict[Literal['Solo/Duo', 'Flex'], Rank]


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
    id: str
    start_time: int
    duration: int
    winner: Literal['Red', 'Blue', 'Remake']
    participants: List[PlayerInfo]
    queue_type: QueueType

    def get_player(self, id: str):
        p = [p for p in self.participants if p.id == id]
        return p[0] if len(p) else None

    @classmethod
    def empty(cls):
        return cls('-1', 0, 0, 'Remake', [], 'Other')

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


RANK_DIVISIONS: List[RankOption] = ['UNRANKED', 'IRON', 'BRONZE', 'SILVER',
                                    'GOLD', 'PLATINUM', 'EMERALD', 'DIAMOND',
                                    'MASTER', 'GRANDMASTER', 'CHALLENGER']

RANK_TIERS: List[Optional[TierOption]] = [None, 'IV', 'III', 'II', 'I']


@dataclass
class Rank:
    division: RankOption
    tier: Optional[TierOption]
    lp: int
    wins: int
    losses: int

    def full(self):
        name = self.division
        if self.tier:
            name += f" {self.tier}"
        return name

    def id(self) -> int:
        '''
        Returns a unique score to distinguish different divisions, tiers, and lp.
        A higher id means that the rank is higher quality.
        '''
        total = RANK_DIVISIONS.index(self.division) * 1000
        total += RANK_TIERS.index(self.tier) * 150
        total += self.lp
        return total

    def is_same_as(self, other: Self):
        return self.division == other.division and self.tier == other.tier

    def games(self):
        return self.wins + self.losses

    def winrate(self):
        return f'{self.wins / self.games() * 100:.2f}%'

    def info(self):
        s = ''
        if self.division != 'UNRANKED':
            s += str(self.lp) + ' LP, '
        s += f'{self.games()} games'
        if self.games() > 0:
            s += f', {self.winrate()} WR'
        return s

    @classmethod
    def from_data(cls, rankData: APILeagueEntry):
        if rankData['tier'] in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
            tier = None
        else:
            tier = cast(TierOption, rankData['rank'])

        return cls(
            cast(RankOption, rankData['tier']),
            tier,
            rankData['leaguePoints'],
            rankData['wins'],
            rankData['losses']
        )

    @classmethod
    def unranked(cls):
        return cls('UNRANKED', None, 0, 0, 0)


@dataclass
class UserInfo:
    id: str = ''
    puuid: str = ''
    summoner_name: str = 'Unknown User'
    summoner_tag: str = ''
    level: int = 0
    icon: int = 1
    ranks: RanksDict = field(default_factory=dict)
    top_champs: List[UserChamp] = field(default_factory=list)
    total_points: int = 0
    total_mastery: int = 0

    @property
    def max_division(self):
        if self.ranks['Flex'].id() > self.ranks['Solo/Duo'].id():
            return self.ranks['Flex'].division
        return self.ranks['Solo/Duo'].division

    def copy(self):
        '''Returns a deep copy of the user object'''
        champs = [replace(c) for c in self.top_champs]
        ranks = {
            mode: replace(rank)
            for mode, rank in self.ranks.items()
        }
        return replace(self, ranks=ranks, top_champs=champs)
