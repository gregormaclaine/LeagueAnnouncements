from typing import Literal, Optional, Generic, TypeVar, TypedDict, Final
from logs import log

T = TypeVar('T')

type APIError = Literal['unknown', 'rate-limit', 'invalid-api-key', 'unknown',
                        'not-found', 'server-internal', 'bad-gateway', 'gateway-timeout']


class APIResponse(Generic[T]):
    ERROR_TYPES: Final[dict[int, Optional[APIError]]] = {
        200: None,

        # Request Errors
        403: 'invalid-api-key',
        404: 'not-found',
        429: 'rate-limit',

        # Server Errors
        500: 'server-internal',
        502: 'bad-gateway',
        504: 'gateway-timeout'
    }

    ERROR_MSG: Final[dict[int, str]] = {
        403: 'Riot API key is invalid',
        404: 'Couldn\'t find item',
        429: 'Riot API was rate-limited',
        500: 'Riot API experience internal issues (500)',
        502: 'Riot API experience internal issues (502)',
        504: 'Riot API experience internal issues (504)',
    }

    def __init__(self, status: int = 200, data: T = None):
        self.status = status
        self.data = data

    def error(self) -> Optional[APIError]:
        return self.ERROR_TYPES.get(self.status, 'unknown')

    def is_server_err(self) -> bool:
        return self.status != 200 and self.status >= 500

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
            log('Error: ' + self.ERROR_MSG[self.status], 'ERROR', source)


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
