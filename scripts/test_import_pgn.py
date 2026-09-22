import unittest
from import_pgn import prepare_pgn, slugify


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

    def test_slug_drops_ccc_label_and_time_control(self):
        self.assertEqual(slugify('CCC 26 Bullet: Semifinals'), '26-bullet-semifinals')
        self.assertEqual(slugify('CCC 22 Rapid: Tiebreaker #1 (10|3)'), '22-rapid-tiebreaker-1')
        self.assertEqual(slugify('CCC 12.0: Houdini vs Stoofvlees (1|1)'), '12-0-houdini-vs-stoofvlees')
        self.assertEqual(slugify('16:1 Odds: Reckless vs Stockfish (1|1)'), '16-1-odds-reckless-vs-stockfish')

    def test_filename_is_start_date_plus_slug(self):
        content = game('2026-08-29', '2026-08-29').replace(b'CCC Test', b'CCC 26 Bullet: Semifinals')
        _, metadata, _ = prepare_pgn(content)
        self.assertEqual(metadata['zip'], 'ccc_2026-08-29_26-bullet-semifinals.zip')
        self.assertEqual(metadata['pgn'], 'ccc_2026-08-29_26-bullet-semifinals.pgn')


if __name__ == '__main__':
    unittest.main()
