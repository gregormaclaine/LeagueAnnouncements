from typing import Literal, Union, Generic, TypeVar, TypedDict
from logs import log

T = TypeVar('T')


class APIResponse(Generic[T]):
    ERROR_TYPES = {
        200: None,
        403: 'invalid-api-key',
        429: 'rate-limit',
        404: 'not-found'
    }

    def __init__(self, status: int = 200, data: T = None):
        self.status = status
        self.data = data

    def error(self) -> Union[None, Literal['rate-limit', 'invalid-api-key', 'unknown', 'not-found']]:
        return self.ERROR_TYPES.get(self.status, 'unknown')

    async def respond_if_error(self, send_message) -> bool:
        '''Respond to discord command if error occured. Returns whether an error occured'''
        error = self.error()
        if error is None:
            return False

        if error == 'rate-limit':
            log('Error: Riot API was rate-limited', 'ERROR')
            await send_message('Error: Riot API was rate-limited')
        elif error == 'invalid-api-key':
            log('Error: Riot API key is invalid', 'ERROR')
            await send_message('Error: Riot API key is invalid')
        else:
            log(f'Error: An unknown error ({
                self.status}) occured - {self.data}', 'ERROR')
            await send_message('Error: An unknown error occured')
        return True


class APISummoner(TypedDict):
    accountId: str
    profileIconId: int
    revisionDate: int
    name: str
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
