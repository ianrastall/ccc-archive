# ccc-archive
Zipped PGNs of the Chesscom CCC.

## Data and naming

ZIPs live in year folders. Each contains one matching PGN, for example
`2026/cc_ccc_260824.zip` → `cc_ccc_260824.pgn`. Filenames follow
`cc_ccc_YYMMDD[a|b|c…].(zip|pgn)`, keyed on the event start date. When two or
more events share a start date, `a`, `b`, `c…` are assigned in the order the
events were added to the manifest. The manifest keeps the full `start` and `end`
date range and the event name; only the filename is compressed to the start
date.

## Import local event downloads

Preview selected files with Python 3.10 or later:

```powershell
python scripts/import_pgn.py D:\dev\pgn\ccc2\event-501.pgn D:\dev\pgn\ccc2\event-503.pgn
```

Add `--write` to create canonical ZIPs and update `ccc_manifest.json`,
`ccc_links.txt`, `events.txt`, and `game_counts.txt`. The importer leaves source
files in place, refuses existing or overlapping archives, and verifies ZIP
contents before updating metadata. Select only events not already imported.

Date ranges use the earliest game start and latest game end, including files
whose games are out of order. Bare Event-only placeholders are omitted from the
archived copy and game counts. Valid game blocks, engine annotations, and `*`
results are preserved. The import report identifies omitted placeholders.

Run the importer tests with `python -m unittest discover -s scripts -p 'test_*.py'`.

Publish this repository before refreshing Chess Nerd. Its page at
https://chessnerd.net/ccc-archive.html reads this repository's published manifest
on each site deployment. For a local site snapshot, run `npm run sync:ccc` in
the Chess Nerd repository.
