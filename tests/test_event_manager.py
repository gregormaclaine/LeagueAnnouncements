import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock

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

# img_gen uses PIL and font files; mock it so importing events doesn't fail
sys.modules.setdefault('img_gen', MagicMock())

from riot.structs import Rank, UserInfo, GameInfo, PlayerInfo  # noqa: E402
from riot.responses import APIResponse  # noqa: E402
from events import LowKDAEvent, LoseStreakEvent, RankChangeEvent, TotalGamesEvent  # noqa: E402
from event_manager import EventManager  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rank(division='GOLD', tier='IV', lp=50, wins=100, losses=80):
    return Rank(division, tier, lp, wins, losses)


def _user(puuid='test-puuid', name='TestPlayer',
          solo_div='GOLD', solo_tier='IV', solo_wins=100, solo_losses=80):
    return UserInfo(
        puuid=puuid,
        summoner_name=name,
        summoner_tag='EUW',
        level=100,
        icon=1,
        ranks={
            'Solo/Duo': _rank(solo_div, solo_tier, wins=solo_wins, losses=solo_losses),
            'Flex': Rank.unranked(),
        },
    )


def _player(puuid, kills=5, deaths=3, assists=7, team='Blue'):
    return PlayerInfo(
        puuid=puuid,
        summoner_name='TestPlayer',
        kills=kills,
        deaths=deaths,
        assists=assists,
        champion_name='Ahri',
        champion_id=103,
        gold=12000,
        damage=25000,
        creep_score=180,
        vision_score=20,
        team=team,
        multikills=[0, 0, 0, 0],
        position='MIDDLE',
    )


def _game(game_id='game1', winner='Blue', duration=1800, participants=None):
    return GameInfo(game_id, 1_000_000, duration, winner,
                    participants or [], 'Solo/Duo')


def _memory(lose_streak=0, solo_div='GOLD', solo_tier='IV',
            solo_wins=100, solo_losses=80):
    return {
        'last_game': 'game0',
        'last_played': 0,
        'lose_streak': lose_streak,
        'ranks': {
            'Solo/Duo': _rank(solo_div, solo_tier, wins=solo_wins, losses=solo_losses),
            'Flex': Rank.unranked(),
        },
        'level': 100,
        'name': 'TestPlayer',
        'tag': 'EUW',
    }


def _mock_riot():
    r = MagicMock()
    r.get_profile_info = AsyncMock()
    r.get_matches_ids_by_puuid = AsyncMock()
    r.get_match_info_by_id = AsyncMock()
    return r


# ---------------------------------------------------------------------------
# is_milestone_game
# ---------------------------------------------------------------------------

class TestIsMilestoneGame(unittest.TestCase):
    def setUp(self):
        self.em = EventManager(_mock_riot())

    def test_every_50_up_to_250(self):
        for n in [50, 100, 150, 200, 250]:
            with self.subTest(n=n):
                self.assertTrue(self.em.is_milestone_game(n))

    def test_every_100_above_250(self):
        for n in [300, 400, 500, 1000]:
            with self.subTest(n=n):
                self.assertTrue(self.em.is_milestone_game(n))

    def test_non_milestones(self):
        for n in [49, 51, 75, 251, 275, 350]:
            with self.subTest(n=n):
                self.assertFalse(self.em.is_milestone_game(n))

    def test_zero_is_milestone(self):
        # 0 % 50 == 0 and 0 <= 250 — documents this edge case
        self.assertTrue(self.em.is_milestone_game(0))


# ---------------------------------------------------------------------------
# find_events_from_games
# ---------------------------------------------------------------------------

class TestFindEventsFromGames(unittest.TestCase):
    def setUp(self):
        self.em = EventManager(_mock_riot())
        self.user = _user()

    def test_bad_kda_creates_low_kda_event(self):
        p = _player(self.user.puuid, kills=0, deaths=5, assists=0, team='Blue')
        game = _game(winner='Blue', participants=[p])
        mem = _memory()
        events = self.em.find_events_from_games(self.user, [game], mem)
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], LowKDAEvent)

    def test_perfect_kda_no_low_kda_event(self):
        p = _player(self.user.puuid, kills=5, deaths=0, assists=3, team='Blue')
        game = _game(winner='Blue', participants=[p])
        mem = _memory()
        events = self.em.find_events_from_games(self.user, [game], mem)
        kda_events = [e for e in events if isinstance(e, LowKDAEvent)]
        self.assertEqual(len(kda_events), 0)

    def test_kda_at_threshold_no_event(self):
        # Exactly 1.0 KDA — should NOT trigger LowKDAEvent
        p = _player(self.user.puuid, kills=1, deaths=2, assists=1, team='Blue')
        # KDA = (1+1)/2 = 1.0
        game = _game(winner='Blue', participants=[p])
        mem = _memory()
        events = self.em.find_events_from_games(self.user, [game], mem)
        kda_events = [e for e in events if isinstance(e, LowKDAEvent)]
        self.assertEqual(len(kda_events), 0)

    def test_three_consecutive_losses_creates_lose_streak_event(self):
        # games list is newest-first; reversed() processes oldest first
        p_loss = _player(self.user.puuid, kills=1, deaths=1, assists=1, team='Red')
        g1 = _game('g1', winner='Blue', participants=[p_loss])
        g2 = _game('g2', winner='Blue', participants=[p_loss])
        g3 = _game('g3', winner='Blue', participants=[p_loss])
        mem = _memory(lose_streak=0)
        events = self.em.find_events_from_games(self.user, [g3, g2, g1], mem)
        streak_events = [e for e in events if isinstance(e, LoseStreakEvent)]
        self.assertEqual(len(streak_events), 1)
        self.assertEqual(streak_events[0].streak, 3)

    def test_win_resets_streak(self):
        p_loss = _player(self.user.puuid, kills=1, deaths=1, assists=1, team='Red')
        p_win = _player(self.user.puuid, kills=3, deaths=1, assists=2, team='Blue')
        # Processed oldest→newest: loss, loss, win, loss
        g_old2 = _game('g1', winner='Blue', participants=[p_loss])
        g_old1 = _game('g2', winner='Blue', participants=[p_loss])
        g_win = _game('g3', winner='Blue', participants=[p_win])
        g_new = _game('g4', winner='Blue', participants=[p_loss])
        mem = _memory(lose_streak=0)
        events = self.em.find_events_from_games(
            self.user, [g_new, g_win, g_old1, g_old2], mem)
        streak_events = [e for e in events if isinstance(e, LoseStreakEvent)]
        self.assertEqual(len(streak_events), 0)
        self.assertEqual(mem['lose_streak'], 1)

    def test_remake_skipped_for_streak(self):
        p = _player(self.user.puuid, kills=3, deaths=1, assists=5, team='Blue')
        remake = _game('r1', winner='Remake', participants=[p])
        mem = _memory(lose_streak=2)
        self.em.find_events_from_games(self.user, [remake], mem)
        # Streak must not change — remake is skipped entirely
        self.assertEqual(mem['lose_streak'], 2)


# ---------------------------------------------------------------------------
# get_ordered_rankings / get_ordered_total_games
# ---------------------------------------------------------------------------

class TestGetOrderedRankings(unittest.TestCase):
    def setUp(self):
        self.em = EventManager(_mock_riot())

    def _seed(self, puuid, division, tier='I', lp=0, wins=100, losses=50):
        self.em.player_memory[puuid] = _memory(
            solo_div=division, solo_tier=tier, solo_wins=wins, solo_losses=losses)

    def test_sorted_by_rank_id_descending(self):
        self._seed('p1', 'GOLD')
        self._seed('p2', 'PLATINUM')
        self._seed('p3', 'SILVER')
        result = self.em.get_ordered_rankings('Solo/Duo')
        puuids = [r['puuid'] for r in result]
        self.assertEqual(puuids, ['p2', 'p1', 'p3'])

    def test_unranked_excluded(self):
        self._seed('p1', 'GOLD')
        self.em.player_memory['p2'] = _memory(solo_div='UNRANKED', solo_tier=None)
        result = self.em.get_ordered_rankings('Solo/Duo')
        puuids = [r['puuid'] for r in result]
        self.assertIn('p1', puuids)
        self.assertNotIn('p2', puuids)

    def test_empty_memory_returns_empty(self):
        result = self.em.get_ordered_rankings('Solo/Duo')
        self.assertEqual(result, [])


class TestGetOrderedTotalGames(unittest.TestCase):
    def setUp(self):
        self.em = EventManager(_mock_riot())

    def _seed(self, puuid, wins, losses):
        self.em.player_memory[puuid] = _memory(solo_wins=wins, solo_losses=losses)

    def test_sorted_by_games_descending(self):
        self._seed('p1', wins=50, losses=50)   # 100 games
        self._seed('p2', wins=80, losses=120)  # 200 games
        self._seed('p3', wins=10, losses=20)   # 30 games
        result = self.em.get_ordered_total_games('Solo/Duo')
        puuids = [r['puuid'] for r in result]
        self.assertEqual(puuids, ['p2', 'p1', 'p3'])

    def test_zero_games_excluded(self):
        self._seed('p1', wins=50, losses=50)
        self._seed('p2', wins=0, losses=0)   # 0 games → excluded
        result = self.em.get_ordered_total_games('Solo/Duo')
        puuids = [r['puuid'] for r in result]
        self.assertIn('p1', puuids)
        self.assertNotIn('p2', puuids)


# ---------------------------------------------------------------------------
# remember_history
# ---------------------------------------------------------------------------

class TestRememberHistory(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.riot = _mock_riot()
        self.em = EventManager(self.riot)
        self.user = _user()

    def _make_game_result(self, game_id, user_wins):
        team = 'Blue' if user_wins else 'Red'
        p = _player(self.user.puuid, team=team)
        return _game(game_id, winner='Blue', participants=[p])

    async def test_no_losses_streak_zero(self):
        # Most recent game is a win → break immediately, streak = 0
        win_game = self._make_game_result('g1', user_wins=True)
        self.riot.get_match_info_by_id.return_value = win_game
        await self.em.remember_history(self.user, ['g1', 'g2'])
        self.assertEqual(self.em.player_memory[self.user.puuid]['lose_streak'], 0)

    async def test_consecutive_losses_counted(self):
        # History (newest first): loss, loss, loss, win
        results = {
            'g_loss3': self._make_game_result('g_loss3', user_wins=False),
            'g_loss2': self._make_game_result('g_loss2', user_wins=False),
            'g_loss1': self._make_game_result('g_loss1', user_wins=False),
            'g_win':   self._make_game_result('g_win',   user_wins=True),
        }
        self.riot.get_match_info_by_id.side_effect = lambda gid: results[gid]
        await self.em.remember_history(
            self.user, ['g_loss3', 'g_loss2', 'g_loss1', 'g_win'])
        self.assertEqual(self.em.player_memory[self.user.puuid]['lose_streak'], 3)

    async def test_remake_skipped(self):
        # History: loss, remake, loss, win
        # Remake must not count as loss or break the streak
        p = _player(self.user.puuid, team='Red')
        remake_game = _game('r1', winner='Remake', participants=[p])
        loss_game = self._make_game_result('g_loss', user_wins=False)
        win_game = self._make_game_result('g_win', user_wins=True)

        results = {
            'g_loss_new': loss_game,
            'r1': remake_game,
            'g_loss_old': loss_game,
            'g_win': win_game,
        }
        self.riot.get_match_info_by_id.side_effect = lambda gid: results[gid]
        await self.em.remember_history(
            self.user, ['g_loss_new', 'r1', 'g_loss_old', 'g_win'])
        # remake in the middle doesn't add to the count
        self.assertEqual(self.em.player_memory[self.user.puuid]['lose_streak'], 2)

    async def test_last_game_and_level_stored(self):
        win_game = self._make_game_result('g1', user_wins=True)
        self.riot.get_match_info_by_id.return_value = win_game
        await self.em.remember_history(self.user, ['g1'])
        mem = self.em.player_memory[self.user.puuid]
        self.assertEqual(mem['last_game'], 'g1')
        self.assertEqual(mem['level'], self.user.level)
        self.assertEqual(mem['name'], self.user.summoner_name)


# ---------------------------------------------------------------------------
# check_user
# ---------------------------------------------------------------------------

class TestCheckUser(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.riot = _mock_riot()
        self.em = EventManager(self.riot)
        self.puuid = 'player-puuid'

    def _user_with_rank(self, division='GOLD', tier='IV', wins=75, losses=50):
        return _user(puuid=self.puuid, solo_div=division, solo_tier=tier,
                     solo_wins=wins, solo_losses=losses)

    def _win_game(self, game_id):
        p = _player(self.puuid, kills=5, deaths=2, assists=3, team='Blue')
        return _game(game_id, winner='Blue', participants=[p])

    async def test_first_time_player_returns_empty(self):
        user = self._user_with_rank()
        self.riot.get_profile_info.return_value = APIResponse(200, user)
        self.riot.get_matches_ids_by_puuid.return_value = APIResponse(
            200, ['g1', 'g2'])
        self.riot.get_match_info_by_id.return_value = self._win_game('g1')

        events = await self.em.check_user(self.puuid)

        self.assertEqual(events, [])
        self.assertIn(self.puuid, self.em.player_memory)

    async def test_no_new_games_returns_empty(self):
        user = self._user_with_rank(wins=75, losses=50)  # 125 games, not a milestone
        self.em.player_memory[self.puuid] = _memory(
            solo_div='GOLD', solo_tier='IV', solo_wins=75, solo_losses=50)
        self.em.player_memory[self.puuid]['last_game'] = 'g_last'

        self.riot.get_profile_info.return_value = APIResponse(200, user)
        self.riot.get_matches_ids_by_puuid.return_value = APIResponse(
            200, ['g_last', 'g_older'])
        self.riot.get_match_info_by_id.return_value = self._win_game('g_last')

        events = await self.em.check_user(self.puuid)

        self.assertEqual(events, [])

    async def test_rank_change_creates_rank_change_event(self):
        # Memory has GOLD IV; user comes back at GOLD I (different tier)
        self.em.player_memory[self.puuid] = _memory(
            solo_div='GOLD', solo_tier='IV', solo_wins=75, solo_losses=50)
        self.em.player_memory[self.puuid]['last_game'] = 'g_last'

        user = _user(puuid=self.puuid, solo_div='GOLD', solo_tier='I',
                     solo_wins=76, solo_losses=50)
        self.riot.get_profile_info.return_value = APIResponse(200, user)
        self.riot.get_matches_ids_by_puuid.return_value = APIResponse(
            200, ['g_new', 'g_last'])
        self.riot.get_match_info_by_id.return_value = self._win_game('g_new')

        events = await self.em.check_user(self.puuid)

        rank_events = [e for e in events if isinstance(e, RankChangeEvent)]
        self.assertEqual(len(rank_events), 1)
        self.assertEqual(rank_events[0].mode, 'Solo/Duo')

    async def test_milestone_game_creates_total_games_event(self):
        # Memory has 99 games; user comes back with 100 (milestone)
        self.em.player_memory[self.puuid] = _memory(
            solo_div='GOLD', solo_tier='IV', solo_wins=60, solo_losses=39)  # 99 games
        self.em.player_memory[self.puuid]['last_game'] = 'g_last'

        user = _user(puuid=self.puuid, solo_div='GOLD', solo_tier='IV',
                     solo_wins=60, solo_losses=40)  # 100 games
        self.riot.get_profile_info.return_value = APIResponse(200, user)
        self.riot.get_matches_ids_by_puuid.return_value = APIResponse(
            200, ['g_new', 'g_last'])
        self.riot.get_match_info_by_id.return_value = self._win_game('g_new')

        events = await self.em.check_user(self.puuid)

        milestone_events = [e for e in events if isinstance(e, TotalGamesEvent)]
        self.assertEqual(len(milestone_events), 1)
        self.assertEqual(milestone_events[0].mode, 'Solo/Duo')

    async def test_deleted_user_added_to_deleted_set(self):
        self.riot.get_profile_info.return_value = APIResponse(404, None)
        self.em.player_memory[self.puuid] = _memory()
        self.em.player_memory[self.puuid]['name'] = 'TestPlayer'
        self.em.player_memory[self.puuid]['tag'] = 'EUW'

        events = await self.em.check_user(self.puuid)

        self.assertEqual(events, [])
        self.assertIn(self.puuid, self.em.deleted_users)


if __name__ == '__main__':
    unittest.main()
