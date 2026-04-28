import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

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

from storage import MemoryEncoder, extract_from_data  # noqa: E402
import storage  # noqa: E402


class TestMemoryEncoder(unittest.TestCase):
    def test_set_serialized_to_list(self):
        data = {'users': {3, 1, 2}}
        result = json.loads(json.dumps(data, cls=MemoryEncoder))
        self.assertIsInstance(result['users'], list)
        self.assertEqual(sorted(result['users']), [1, 2, 3])

    def test_datetime_serialized_to_isoformat(self):
        dt = datetime(2024, 6, 15, 12, 30, 0)
        result = json.loads(json.dumps({'time': dt}, cls=MemoryEncoder))
        self.assertEqual(result['time'], '2024-06-15T12:30:00')

    def test_unknown_type_raises(self):
        with self.assertRaises(TypeError):
            json.dumps({'obj': object()}, cls=MemoryEncoder)


class TestExtractFromData(unittest.TestCase):
    def _make_memory(self, guild_key='123', claimed_users=None,
                     with_files=False, include_deleted=False):
        player = {
            'puuid': 'test-puuid',
            'name': 'TestPlayer',
            'tag': 'EUW',
            'level': 100,
            'claimed_users': claimed_users if claimed_users is not None else [456, 789],
        }
        if include_deleted:
            player['deleted'] = True

        mem = {
            'tracked_players': {guild_key: [player]},
            'output_channels': {guild_key: 999},
            'allotted_files': [],
        }
        if with_files:
            dt = datetime(2025, 1, 1, 12, 0, 0)
            mem['allotted_files'] = [{
                'name': 'f.png',
                'path': '/tmp/f.png',
                'expiry': dt.isoformat(),
            }]
        return mem

    def test_guild_keys_cast_to_int(self):
        mem = self._make_memory(guild_key='12345')
        tracked, channels, _ = extract_from_data(mem)
        self.assertIn(12345, tracked)
        self.assertIn(12345, channels)
        self.assertNotIn('12345', tracked)

    def test_claimed_users_list_to_set(self):
        mem = self._make_memory(claimed_users=[100, 200, 300])
        tracked, _, _ = extract_from_data(mem)
        player = list(tracked.values())[0][0]
        self.assertIsInstance(player['claimed_users'], set)
        self.assertEqual(player['claimed_users'], {100, 200, 300})

    def test_expiry_string_to_datetime(self):
        mem = self._make_memory(with_files=True)
        _, _, files = extract_from_data(mem)
        self.assertEqual(len(files), 1)
        self.assertIsInstance(files[0]['expiry'], datetime)
        self.assertEqual(files[0]['expiry'], datetime(2025, 1, 1, 12, 0, 0))

    def test_missing_deleted_defaults_false(self):
        mem = self._make_memory()  # no 'deleted' key in player
        tracked, _, _ = extract_from_data(mem)
        player = list(tracked.values())[0][0]
        self.assertFalse(player['deleted'])

    def test_empty_allotted_files_key_missing(self):
        mem = self._make_memory()
        del mem['allotted_files']
        _, _, files = extract_from_data(mem)
        self.assertEqual(files, [])

    def test_multiple_guilds(self):
        mem = {
            'tracked_players': {'1': [], '2': []},
            'output_channels': {'1': 100, '2': 200},
            'allotted_files': [],
        }
        tracked, channels, _ = extract_from_data(mem)
        self.assertIn(1, tracked)
        self.assertIn(2, tracked)
        self.assertEqual(channels[1], 100)
        self.assertEqual(channels[2], 200)


class TestClearExpiredFiles(unittest.TestCase):
    def setUp(self):
        storage.allotted_files.clear()

    def tearDown(self):
        storage.allotted_files.clear()

    def test_expired_file_removed_from_list(self):
        storage.allotted_files.append({
            'name': 'old.png',
            'path': '/tmp/old.png',
            'expiry': datetime.now() - timedelta(hours=1),
        })
        with patch('storage.remove'):
            storage.clear_expired_files()
        self.assertEqual(len(storage.allotted_files), 0)

    def test_expired_file_calls_remove(self):
        storage.allotted_files.append({
            'name': 'old.png',
            'path': '/tmp/old.png',
            'expiry': datetime.now() - timedelta(hours=1),
        })
        with patch('storage.remove') as mock_rm:
            storage.clear_expired_files()
        mock_rm.assert_called_once_with('/tmp/old.png')

    def test_unexpired_file_kept(self):
        storage.allotted_files.append({
            'name': 'new.png',
            'path': '/tmp/new.png',
            'expiry': datetime.now() + timedelta(hours=1),
        })
        with patch('storage.remove') as mock_rm:
            storage.clear_expired_files()
        mock_rm.assert_not_called()
        self.assertEqual(len(storage.allotted_files), 1)

    def test_only_expired_removed_when_mixed(self):
        storage.allotted_files.append({
            'name': 'old.png',
            'path': '/tmp/old.png',
            'expiry': datetime.now() - timedelta(hours=1),
        })
        storage.allotted_files.append({
            'name': 'new.png',
            'path': '/tmp/new.png',
            'expiry': datetime.now() + timedelta(hours=1),
        })
        with patch('storage.remove'):
            storage.clear_expired_files()
        self.assertEqual(len(storage.allotted_files), 1)
        self.assertEqual(storage.allotted_files[0]['name'], 'new.png')


if __name__ == '__main__':
    unittest.main()
