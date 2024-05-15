from typing import Literal, Optional, TypedDict, Final, List
from logs import log

type APIError = Literal['unknown', 'rate-limit', 'invalid-api-key', 'unknown',
                        'not-found', 'server-internal', 'bad-gateway', 'gateway-timeout', 'client-connection-error']


class APIResponse[T]:
    ERROR_TYPES: Final[dict[int, Optional[APIError]]] = {
        200: None,

        # Request Errors
        403: 'invalid-api-key',
        404: 'not-found',
        429: 'rate-limit',
        499: 'client-connection-error',

        # Server Errors
        500: 'server-internal',
        502: 'bad-gateway',
        504: 'gateway-timeout'
    }

    ERROR_MSG: Final[dict[int, str]] = {
        403: 'Riot API key is invalid',
        404: 'Couldn\'t find item',
        429: 'Riot API was rate-limited',
        499: 'Couldn\'t connect to server',
        500: 'Riot API experience internal issues (500)',
        502: 'Riot API experience internal issues (502)',
        504: 'Riot API experience internal issues (504)',
    }

    status: int
    rate_limit_info: Optional[tuple[str, str]]

    def __init__(self, status: int = 200, data: T = None, rate_limit_count: Optional[str] = None, rate_limit: Optional[str] = None):
        self.status = status
        self.data = data

        if rate_limit and rate_limit_count:
            self.rate_limit_info = (rate_limit_count, rate_limit)

    def error(self) -> Optional[APIError]:
        return self.ERROR_TYPES.get(self.status, 'unknown')

    def is_server_err(self) -> bool:
        return self.status != 200 and self.status >= 500

    def rate_limit_count(self, which: int = 1) -> int:
        if self.rate_limit_info is None:
            return -1
        if info := self.rate_limit_info[0]:
            return int(info.split(',')[which].split(':')[0])
        return -1

    async def respond_if_error(self, send_message) -> bool:
        '''Respond to discord command if error occured. Returns whether an error occured'''
        error = self.error()
        if error is None:
            return False

        self.log_error(1)
        if error == 'rate-limit':
            await send_message('Error: Riot API was rate-limited')
        elif error == 'invalid-api-key':
            await send_message('Error: Riot API key is invalid')
        elif self.is_server_err():
            await send_message('Error: Riot API did not respond')
        else:
            await send_message('Error: An unknown error occured')
        return True

    def log_error(self, place_id: int, msg: str = '', source: str = 'main.riot_api') -> None:
        source = f'{source}[{str(place_id).zfill(3)}]'
        log('Error: ' + msg, 'ERROR', source)

        if self.error() == 'unknown':
            log(f'Error: An unknown error ({
                self.status}) occured - {self.data}', 'ERROR', source)
        else:
            log('Error: ' + self.ERROR_MSG.get(self.status,
                f'Unknown error ({self.status})'), 'ERROR', source)


class APISummonerName(TypedDict):
    puuid: str
    gameName: str
    tagLine: str


class APISummoner(TypedDict):
    accountId: str
    profileIconId: int
    revisionDate: int
    id: str
    puuid: str
    summonerLevel: int


class APIRiotAccount(TypedDict):
    puuid: str
    gameName: str
    tagLine: str


class APIMiniSeries(TypedDict):
    losses: int
    progress: str
    target: int
    wins: int


class APILeagueEntry(TypedDict):
    leagueId: str
    summonerId: str
    summonerName: str
    queueType: str
    tier: str
    rank: str
    leaguePoints: int
    wins: int
    losses: int
    hotStreak: bool
    veteran: bool
    freshBlood: bool
    inactive: bool
    miniSeries: APIMiniSeries


class APIMatchMetadata(TypedDict):
    dataVersion: str
    matchId: str
    participants: List[str]


class APIMatchParticipantPerkStats(TypedDict):
    defense: int
    flex: int
    offense: int


class APIMatchParticipantPerkStyleSelection(TypedDict):
    perk: int
    var1: int
    var2: int
    var3: int


class APIMatchParticipantPerkStyle(TypedDict):
    description: str
    selections: List[APIMatchParticipantPerkStyleSelection]
    style: int


class APIMatchParticipantPerks(TypedDict):
    statPerks: APIMatchParticipantPerkStats
    styles: List[APIMatchParticipantPerkStyle]


class APIMatchParticipant(TypedDict):
    assists: int
    baronKills: int
    bountyLevel: int
    champExperience: int
    champLevel: int
    championId: int
    championName: str
    # Kayn transform (0: None, 1: Slayer, 2: Assassin)
    championTransform: Literal[0, 1, 2]
    consumablesPurchased: int
    damageDealtToBuildings: int
    damageDealtToObjectives: int
    damageDealtToTurrets: int
    damageSelfMitigated: int
    deaths: int
    detectorWardsPlaced: int
    doubleKills: int
    dragonKills: int
    firstBloodAssist: bool
    firstBloodKill: bool
    firstTowerAssist: bool
    firstTowerKill: bool
    gameEndedInEarlySurrender: bool
    gameEndedInSurrender: bool
    goldEarned: int
    goldSpent: int
    individualPosition: Literal['UTILITY', 'BOTTOM', 'MIDDLE', 'JUNGLE', 'TOP']
    inhibitorKills: int
    inhibitorTakedowns: int
    inhibitorsLost: int
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int
    itemsPurchased: int
    killingSprees: int
    kills: int
    lane: str
    largestCriticalStrike: int
    largestKillingSpree: int
    largestMultiKill: int
    longestTimeSpentLiving: int
    magicDamageDealt: int
    magicDamageDealtToChampions: int
    magicDamageTaken: int
    neutralMinionsKilled: int
    nexusKills: int
    nexusTakedowns: int
    nexusLost: int
    objectivesStolen: int
    objectivesStolenAssists: int
    participantId: int
    pentaKills: int
    perks: APIMatchParticipantPerks
    physicalDamageDealt: int
    physicalDamageDealtToChampions: int
    physicalDamageTaken: int
    profileIcon: int
    puuid: str
    quadraKills: int
    riotIdName: str
    riotIdTagline: str
    role: str
    sightWardsBoughtInGame: int
    spell1Casts: int
    spell2Casts: int
    spell3Casts: int
    spell4Casts: int
    summoner1Casts: int
    summoner1Id: int
    summoner2Casts: int
    summoner2Id: int
    summonerId: str
    summonerLevel: int
    summonerName: str
    teamEarlySurrendered: bool
    teamId: int
    teamPosition: Literal['UTILITY', 'BOTTOM', 'MIDDLE', 'JUNGLE', 'TOP']
    timeCCingOthers: int
    timePlayed: int
    totalDamageDealt: int
    totalDamageDealtToChampions: int
    totalDamageShieldedOnTeammates: int
    totalDamageTaken: int
    totalHeal: int
    totalHealsOnTeammates: int
    totalMinionsKilled: int
    totalTimeCCDealt: int
    totalTimeSpentDead: int
    totalUnitsHealed: int
    tripleKills: int
    trueDamageDealt: int
    trueDamageDealtToChampions: int
    trueDamageTaken: int
    turretKills: int
    turretTakedowns: int
    turretsLost: int
    unrealKills: int
    visionScore: int
    visionWardsBoughtInGame: int
    wardsKilled: int
    wardsPlaced: int
    win: bool


class APIMatchBan(TypedDict):
    championId: int
    pickTurn: int


class ApiMatchObjective(TypedDict):
    first: bool
    kills: int


class APIMatchObjectives(TypedDict):
    baron: ApiMatchObjective
    champion: ApiMatchObjective
    dragon: ApiMatchObjective
    inhibitor: ApiMatchObjective
    riftHerald: ApiMatchObjective
    tower: ApiMatchObjective


class APIMatchTeam(TypedDict):
    bans: List[APIMatchBan]
    objectives:	APIMatchObjectives
    teamId:	int
    win: bool


class APIMatchInfo(TypedDict):
    # Can't seem to find other options of endOfGameResult
    endOfGameResult: Literal['GameComplete']
    gameCreation: int
    gameDuration: int
    gameEndTimestamp: int
    gameId: int
    gameMode: str
    gameName: str
    gameStartTimestamp: int
    gameType: str
    gameVersion: str
    mapId: int
    participants: List[APIMatchParticipant]
    platformId: str
    queueId: int
    teams: List[APIMatchTeam]
    tournamentCode: str


class APIMatch(TypedDict):
    metadata: APIMatchMetadata
    info: APIMatchInfo
