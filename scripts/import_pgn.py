#!/usr/bin/env python3
"""Add selected CCC PGNs without modifying sources or replacing existing archives."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT_START = re.compile(rb'(?m)(?=^\[Event )')
TAG = re.compile(rb'^\[([A-Za-z0-9_]+) "(.*)"\]\s*$')
RESULTS = {b'1-0', b'0-1', b'1/2-1/2', b'*'}


def game_date(tags: dict[bytes, bytes], preferred: bytes) -> str:
    value = tags.get(preferred) or tags.get(b'Date', b'')
    # CCC timestamps include a T separator and a timezone after the date.
    return date.fromisoformat(value[:10].decode().replace('.', '-')).strftime('%y%m%d')


def prepare_pgn(content: bytes) -> tuple[bytes, dict, int]:
    kept, starts, ends, events = [], [], [], set()
    skipped = 0
    for block in EVENT_START.split(content.removeprefix(b'\xef\xbb\xbf')):
        if not block.strip():
            continue
        tags = {}
        lines = block.splitlines()
        move_index = None
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            match = TAG.fullmatch(line)
            if not match:
                move_index = index
                break
            tags[match[1]] = match[2]
        if set(tags) == {b'Event'} and move_index is None:
            skipped += 1
            continue
        if move_index is None or not all(tags.get(key) for key in (b'Event', b'White', b'Black', b'Result')):
            raise ValueError('Game is missing required headers or movetext.')
        result = tags[b'Result']
        if result not in RESULTS or block.rstrip().split()[-1] != result:
            raise ValueError('Game result and final movetext token do not agree.')
        starts.append(game_date(tags, b'GameStartTime'))
        ends.append(game_date(tags, b'GameEndTime'))
        events.add(tags[b'Event'].decode('utf-8').strip())
        kept.append(block)
    if not kept or len(events) != 1:
        raise ValueError('Expected one named event with at least one game.')
    event = events.pop()
    start, end = min(starts), max(ends)
    if end < start:
        raise ValueError('Event ends before it starts.')
    # Filename encodes only the start date; end date and event name stay in metadata.
    # Collision suffix (a/b/c…) is assigned in main() based on the existing archive.
    stem = f'cc_ccc_{start}'
    metadata = dict(pgn=f'{stem}.pgn', zip=f'{stem}.zip', year=2000 + int(start[:2]),
                    start=start, end=end, event=event, games=len(kept))
    # Game blocks, engine comments, and unfinished (*) games retain their bytes.
    return b''.join(kept), metadata, skipped


def write_metadata(entries: list[dict]) -> None:
    entries.sort(key=lambda entry: (entry['year'], entry['zip']))
    outputs = {
        'ccc_manifest.json': json.dumps(entries, ensure_ascii=False, indent=2) + '\n',
        'ccc_links.txt': ''.join(f"{entry['url']}\n" for entry in entries),
        'events.txt': ''.join(f"{entry['pgn']}: {entry['event']}\n" for entry in entries),
        'game_counts.txt': ''.join(f"{entry['pgn']}: {entry['games']}\n" for entry in entries),
    }
    for name, content in outputs.items():
        temporary = ROOT / f'{name}.tmp'
        temporary.write_text(content, encoding='utf-8', newline='\n')
        temporary.replace(ROOT / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', type=Path, nargs='+')
    parser.add_argument('--write', action='store_true', help='Create ZIPs and update all four metadata files.')
    args = parser.parse_args()
    entries = json.loads((ROOT / 'ccc_manifest.json').read_text(encoding='utf-8'))
    known = {entry['zip'] for entry in entries}
    pending = []
    # Validate the entire selection before creating any archives.
    for source in args.files:
        content = source.read_bytes()
        pgn, entry, skipped = prepare_pgn(content)
        # Assign the next collision letter for entries sharing the start date.
        base_stem = f"cc_ccc_{entry['start']}"
        for suffix in ('', *(chr(c) for c in range(ord('a'), ord('z') + 1))):
            candidate = f'{base_stem}{suffix}.zip'
            if candidate not in known:
                break
        else:
            raise ValueError(f'Too many CCC events on {entry["start"]} to disambiguate.')
        entry['pgn'] = f'{base_stem}{suffix}.pgn'
        entry['zip'] = candidate
        destination = ROOT / str(entry['year']) / entry['zip']
        if destination.exists():
            raise ValueError(f"Archive already exists: {destination}")
        if any(old['event'].strip() == entry['event'] and old['start'] <= entry['end']
               and entry['start'] <= old['end'] for old in entries):
            raise ValueError(f"Event overlaps an existing archive: {source}")
        known.add(entry['zip'])
        pending.append((source, entry, skipped, hashlib.sha256(content).hexdigest()))
        print(f"{source.name} -> {entry['zip']}: {entry['games']} games; {skipped} empty event stubs omitted", flush=True)
    if not args.write:
        print(f'Validated {len(pending)} events. Pass --write to import.')
        return
    for source, entry, skipped, source_hash in pending:
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != source_hash:
            raise ValueError(f'Source changed during import: {source}')
        pgn, verified, verified_skipped = prepare_pgn(content)
        # Copy collision-assigned pgn/zip onto the fresh parse before comparing.
        verified['pgn'] = entry['pgn']
        verified['zip'] = entry['zip']
        if verified != entry or verified_skipped != skipped:
            raise ValueError(f'Source metadata changed during import: {source}')
        destination = ROOT / str(entry['year']) / entry['zip']
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix('.zip.tmp')
        with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr(entry['pgn'], pgn)
        with zipfile.ZipFile(temporary) as archive:
            if archive.read(entry['pgn']) != pgn:
                raise ValueError(f'ZIP verification failed: {destination}')
        temporary.rename(destination)
        entry['url'] = f"https://github.com/ianrastall/ccc-archive/raw/main/{entry['year']}/{entry['zip']}"
        entry['sha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
        entries.append(entry)
        print(f"Created {entry['zip']} ({destination.stat().st_size:,} bytes)", flush=True)
    write_metadata(entries)
    print(f"Archive now contains {len(entries)} events and {sum(entry['games'] for entry in entries):,} games.")


if __name__ == '__main__':
    main()
