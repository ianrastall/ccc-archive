import unittest
from import_pgn import prepare_pgn


def game(start, end, result='1-0'):
    return (f'[Event "CCC Test"]\n[White "A"]\n[Black "B"]\n[Result "{result}"]\n'
            f'[GameStartTime "{start}T23:59:00 -0700"]\n'
            f'[GameEndTime "{end}T00:01:00 -0700"]\n\n1. e4 {{comment}} e5 {result}\n\n').encode()


class ImportTests(unittest.TestCase):
    def test_dates_use_full_range_even_when_games_are_not_chronological(self):
        content = game('2026-08-21', '2026-08-22') + game('2026-08-20', '2026-08-24')
        output, metadata, skipped = prepare_pgn(content)
        self.assertEqual(output, content)
        self.assertEqual((metadata['start'], metadata['end'], metadata['games']), ('260820', '260824', 2))
        self.assertEqual(skipped, 0)

    def test_omits_only_event_only_stubs(self):
        valid = game('2026-07-31', '2026-07-31')
        output, metadata, skipped = prepare_pgn(b'[Event "CCC Test"]\n\n' * 9 + valid)
        self.assertEqual(output, valid)
        self.assertEqual(metadata['games'], 1)
        self.assertEqual(skipped, 9)

    def test_preserves_unfinished_games(self):
        content = game('2026-08-21', '2026-08-22', '*')
        self.assertEqual(prepare_pgn(content)[0], content)

    def test_rejects_stub_only_file_and_truncated_game(self):
        with self.assertRaises(ValueError):
            prepare_pgn(b'[Event "CCC Test"]\n\n')
        with self.assertRaises(ValueError):
            prepare_pgn(game('2026-08-21', '2026-08-22').replace(b'e5 1-0', b'e5'))


if __name__ == '__main__':
    unittest.main()
