import os
import sys
import unittest
from unittest.mock import MagicMock

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

# img_gen uses PIL and font files; mock before importing events
sys.modules.setdefault('img_gen', MagicMock())

from riot.structs import Rank, UserInfo, GameInfo  # noqa: E402
from events import (  # noqa: E402
    RankChangeEvent, LoseStreakEvent, TotalGamesEvent, LeaderboardChangeEvent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(puuid='p1', name='TestUser', solo_div='GOLD', solo_tier='IV'):
    return UserInfo(
        puuid=puuid,
        summoner_name=name,
        summoner_tag='EUW',
        level=100,
        icon=1,
        ranks={
            'Solo/Duo': Rank(solo_div, solo_tier, 50, 100, 80),
            'Flex': Rank.unranked(),
        },
    )


def _game(game_id='g1', winner='Blue'):
    return GameInfo(game_id, 1_000_000, 1800, winner, [], 'Solo/Duo')


# ---------------------------------------------------------------------------
# RankChangeEvent
# ---------------------------------------------------------------------------

class TestRankChangeEvent(unittest.TestCase):
    def test_rank_dir_promoted(self):
        old_rank = Rank('GOLD', 'IV', 50, 100, 80)
        user = _user(solo_div='GOLD', solo_tier='I')  # Gold I > Gold IV
        event = RankChangeEvent(user, _game(), old_rank=old_rank, mode='Solo/Duo')
        self.assertEqual(event.rank_dir(), 'promoted')

    def test_rank_dir_demoted(self):
        old_rank = Rank('GOLD', 'I', 50, 100, 80)
        user = _user(solo_div='GOLD', solo_tier='IV')  # Gold IV < Gold I
        event = RankChangeEvent(user, _game(), old_rank=old_rank, mode='Solo/Duo')
        self.assertEqual(event.rank_dir(), 'demoted')

    def test_old_and_new_rank_stored(self):
        old_rank = Rank('SILVER', 'I', 90, 50, 50)
        user = _user(solo_div='GOLD', solo_tier='IV')
        event = RankChangeEvent(user, _game(), old_rank=old_rank, mode='Solo/Duo')
        self.assertEqual(event.old_rank, old_rank)
        self.assertEqual(event.new_rank, user.ranks['Solo/Duo'])

    def test_none_game_accepted(self):
        old_rank = Rank('GOLD', 'IV', 0, 0, 0)
        user = _user(solo_div='GOLD', solo_tier='I')
        # RankChangeEvent wraps None with GameInfo.empty() internally
        event = RankChangeEvent(user, None, old_rank=old_rank, mode='Solo/Duo')
        self.assertEqual(event.rank_dir(), 'promoted')


# ---------------------------------------------------------------------------
# LoseStreakEvent
# ---------------------------------------------------------------------------

class TestLoseStreakEvent(unittest.TestCase):
    def test_streak_stored(self):
        event = LoseStreakEvent(_user(), _game(), streak=5)
        self.assertEqual(event.streak, 5)

    def test_type_is_embed(self):
        event = LoseStreakEvent(_user(), _game(), streak=3)
        self.assertEqual(event.type, 'embed')

    def test_user_stored(self):
        user = _user(name='StreakPlayer')
        event = LoseStreakEvent(user, _game(), streak=4)
        self.assertEqual(event.user.summoner_name, 'StreakPlayer')


# ---------------------------------------------------------------------------
# TotalGamesEvent
# ---------------------------------------------------------------------------

class TestTotalGamesEvent(unittest.TestCase):
    def test_type_is_image(self):
        event = TotalGamesEvent(_user(), _game(), mode='Solo/Duo')
        self.assertEqual(event.type, 'image')

    def test_mode_stored(self):
        event = TotalGamesEvent(_user(), _game(), mode='Flex')
        self.assertEqual(event.mode, 'Flex')

    def test_solo_mode_stored(self):
        event = TotalGamesEvent(_user(), _game(), mode='Solo/Duo')
        self.assertEqual(event.mode, 'Solo/Duo')


# ---------------------------------------------------------------------------
# LeaderboardChangeEvent
# ---------------------------------------------------------------------------

class TestLeaderboardChangeEvent(unittest.TestCase):
    def setUp(self):
        self.user1 = _user(puuid='p1', name='OldLeader')
        self.user2 = _user(puuid='p2', name='NewLeader')
        self.game = _game()

    def test_position_stored(self):
        event = LeaderboardChangeEvent(
            3, self.user1, self.user2, self.game, 'Solo/Duo')
        self.assertEqual(event.position, 3)

    def test_old_and_new_user_stored(self):
        event = LeaderboardChangeEvent(
            1, self.user1, self.user2, self.game, 'Solo/Duo')
        self.assertEqual(event.old_user.summoner_name, 'OldLeader')
        self.assertEqual(event.new_user.summoner_name, 'NewLeader')

    def test_mode_stored(self):
        event = LeaderboardChangeEvent(
            2, self.user1, self.user2, self.game, 'Flex')
        self.assertEqual(event.mode, 'Flex')

    def test_base_user_is_new_user(self):
        # BaseGameEvent.user is set to new_user (the overtaker)
        event = LeaderboardChangeEvent(
            1, self.user1, self.user2, self.game, 'Solo/Duo')
        self.assertEqual(event.user.summoner_name, 'NewLeader')


if __name__ == '__main__':
    unittest.main()
