import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

sys.modules.setdefault('logs', MagicMock())

if 'config' not in sys.modules:
    _mock_config = MagicMock()
    _mock_config.LEAGUE_PATCH = '14.10.1'
    _mock_config.IS_DEV = True
    _mock_config_inst = MagicMock()
    _mock_config_inst.FILES_PATH = '/tmp/test_league'
    _mock_config.get_config.return_value = _mock_config_inst
    sys.modules['config'] = _mock_config

from riot.api import RiotAPI  # noqa: E402
from riot.structs import Rank  # noqa: E402
from riot.responses import APIResponse  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_league_entry(queue_type, tier, rank, lp=50, wins=100, losses=80):
    return {
        'queueType': queue_type,
        'tier': tier,
        'rank': rank,
        'leaguePoints': lp,
        'wins': wins,
        'losses': losses,
    }


def _make_participant(puuid, team_id=100, win=True,
                      kills=5, deaths=3, assists=7,
                      champ='Ahri', champ_id=103,
                      position='MIDDLE'):
    return {
        'puuid': puuid,
        'summonerName': 'TestPlayer',
        'teamId': team_id,
        'win': win,
        'kills': kills,
        'deaths': deaths,
        'assists': assists,
        'championName': champ,
        'championId': champ_id,
        'goldEarned': 12000,
        'totalDamageDealtToChampions': 25000,
        'totalMinionsKilled': 150,
        'neutralMinionsKilled': 30,
        'visionScore': 20,
        'individualPosition': position,
        'doubleKills': 0,
        'tripleKills': 1,
        'quadraKills': 0,
        'pentaKills': 0,
    }


def _make_raw_match(participants, duration=1800, queue_id=420, start_time=1_000_000):
    return {
        'info': {
            'gameStartTimestamp': start_time,
            'gameDuration': duration,
            'queueId': queue_id,
            'participants': participants,
        }
    }


# ---------------------------------------------------------------------------
# get_ranked_info
# ---------------------------------------------------------------------------

class TestGetRankedInfo(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.riot = RiotAPI('fake-key', 'euw1', 'europe')

    async def _call(self, api_data, puuid):
        with patch.object(self.riot, 'api',
                          new=AsyncMock(return_value=APIResponse(200, api_data))):
            return await self.riot.get_ranked_info(puuid)

    async def test_both_queues_parsed(self):
        data = [
            _make_league_entry('RANKED_SOLO_5x5', 'GOLD', 'IV', lp=75),
            _make_league_entry('RANKED_FLEX_SR',  'SILVER', 'II', lp=30),
        ]
        result = await self._call(data, 'puuid-both-queues')
        self.assertIsNone(result.error())
        ranks = result.data
        self.assertEqual(ranks['Solo/Duo'].division, 'GOLD')
        self.assertEqual(ranks['Solo/Duo'].tier, 'IV')
        self.assertEqual(ranks['Solo/Duo'].lp, 75)
        self.assertEqual(ranks['Flex'].division, 'SILVER')
        self.assertEqual(ranks['Flex'].tier, 'II')

    async def test_missing_flex_defaults_to_unranked(self):
        data = [_make_league_entry('RANKED_SOLO_5x5', 'GOLD', 'IV')]
        result = await self._call(data, 'puuid-solo-only')
        ranks = result.data
        self.assertEqual(ranks['Solo/Duo'].division, 'GOLD')
        self.assertEqual(ranks['Flex'].division, 'UNRANKED')

    async def test_missing_solo_defaults_to_unranked(self):
        data = [_make_league_entry('RANKED_FLEX_SR', 'SILVER', 'I')]
        result = await self._call(data, 'puuid-flex-only')
        ranks = result.data
        self.assertEqual(ranks['Solo/Duo'].division, 'UNRANKED')
        self.assertEqual(ranks['Flex'].division, 'SILVER')

    async def test_no_ranked_data_both_unranked(self):
        result = await self._call([], 'puuid-no-ranked')
        ranks = result.data
        self.assertEqual(ranks['Solo/Duo'].division, 'UNRANKED')
        self.assertEqual(ranks['Flex'].division, 'UNRANKED')

    async def test_api_error_propagated(self):
        with patch.object(self.riot, 'api',
                          new=AsyncMock(return_value=APIResponse(403, None))):
            result = await self.riot.get_ranked_info('puuid-error')
        self.assertEqual(result.error(), 'invalid-api-key')


# ---------------------------------------------------------------------------
# get_match_info_by_id
# ---------------------------------------------------------------------------

class TestGetMatchInfoById(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.riot = RiotAPI('fake-key', 'euw1', 'europe')

    async def _call(self, raw_match, match_id='match-1'):
        resp = APIResponse(200, raw_match)
        with patch.object(self.riot, 'get_raw_match_info_by_id',
                          new=AsyncMock(return_value=resp)):
            return await self.riot.get_match_info_by_id(match_id)

    async def test_blue_team_wins(self):
        p = _make_participant('p1', team_id=100, win=True)
        raw = _make_raw_match([p])
        game = await self._call(raw)
        self.assertEqual(game.winner, 'Blue')

    async def test_red_team_wins(self):
        p = _make_participant('p1', team_id=200, win=True)
        raw = _make_raw_match([p])
        game = await self._call(raw)
        self.assertEqual(game.winner, 'Red')

    async def test_remake_when_duration_under_300(self):
        p = _make_participant('p1', team_id=100, win=True)
        raw = _make_raw_match([p], duration=240)
        game = await self._call(raw)
        self.assertEqual(game.winner, 'Remake')

    async def test_participant_fields_mapped_correctly(self):
        p = _make_participant(
            puuid='player-puuid',
            team_id=100, win=True,
            kills=7, deaths=2, assists=11,
            champ='Lux', champ_id=99,
            position='UTILITY',
        )
        raw = _make_raw_match([p])
        game = await self._call(raw)

        self.assertEqual(len(game.participants), 1)
        participant = game.participants[0]
        self.assertEqual(participant.puuid, 'player-puuid')
        self.assertEqual(participant.kills, 7)
        self.assertEqual(participant.deaths, 2)
        self.assertEqual(participant.assists, 11)
        self.assertEqual(participant.champion_name, 'Lux')
        self.assertEqual(participant.champion_id, 99)
        self.assertEqual(participant.team, 'Blue')   # teamId=100 → Blue
        self.assertEqual(participant.position, 'UTILITY')
        self.assertEqual(participant.creep_score, 180)  # 150 + 30
        self.assertEqual(participant.multikills, [0, 1, 0, 0])

    async def test_unknown_queue_id_becomes_other(self):
        p = _make_participant('p1')
        raw = _make_raw_match([p], queue_id=9999)
        game = await self._call(raw)
        self.assertEqual(game.queue_type, 'Other')

    async def test_known_queue_id_mapped(self):
        p = _make_participant('p1')
        raw = _make_raw_match([p], queue_id=420)  # Solo/Duo
        game = await self._call(raw)
        self.assertEqual(game.queue_type, 'Solo/Duo')

    async def test_api_error_returns_none(self):
        err_resp = APIResponse(404, None)
        with patch.object(self.riot, 'get_raw_match_info_by_id',
                          new=AsyncMock(return_value=err_resp)):
            result = await self.riot.get_match_info_by_id('bad-id')
        self.assertIsNone(result)

    async def test_game_metadata_stored(self):
        p = _make_participant('p1')
        raw = _make_raw_match([p], start_time=5_000_000, duration=2100)
        game = await self._call(raw, match_id='EUW1_999')
        self.assertEqual(game.id, 'EUW1_999')
        self.assertEqual(game.start_time, 5_000_000)
        self.assertEqual(game.duration, 2100)


if __name__ == '__main__':
    unittest.main()
