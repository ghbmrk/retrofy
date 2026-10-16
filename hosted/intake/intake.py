#!/usr/bin/env python3
"""Retrofy local BG3 metadata intake. Standard library only. No network API."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lspk import safe_inspect, CATEGORIES

APPID = '1086940'
HEADER_LIMIT = 40
MAX_ARCHIVES = 2048
MAX_METADATA = 2 * 1024 * 1024
KNOWN_NAME = re.compile(r'(?i)(?:Assets|Effects|Engine|EngineShaders|Game|GamePlatform|Gustav(?:Dev)?|Shared(?:Dev)?|Materials|Models|Textures(?:_\d+)?|VirtualTextures(?:_\d+)?|Patch\d+(?:_Hotfix\d+)?|DiceSet\d+|English|French|German|Spanish|Polish|Russian|Italian|Chinese|ChineseTraditional|Japanese|Korean|Portuguese|Turkish|Ukrainian)\.pak\Z')

class IntakeError(Exception):
    pass


def regular_bytes(path, limit):
    """Reject links, devices, oversized metadata; never execute game files."""
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise IntakeError('Non-regular input refused.')
        return stream.read(limit), info.st_size


def metadata(path):
    data, size = regular_bytes(path, MAX_METADATA + 1)
    if size > MAX_METADATA or len(data) > MAX_METADATA:
        raise IntakeError('Metadata size limit exceeded.')
    return data.decode('utf-8-sig')


def pairs(text):
    # Only quoted scalar pairs are needed, not executable VDF directives.
    pattern = r'"((?:[^"\\]|\\.)*)"\s+"((?:[^"\\]|\\.)*)"'
    def unescape(s):
        return re.sub(r'\\([\\"])', r'\1', s)
    return [(unescape(k), unescape(v)) for k, v in re.findall(pattern, text)]


def scalar(text, key):
    values = [v for k, v in pairs(text) if k == key]
    if len(values) != 1:
        raise IntakeError('Required installation metadata is missing or ambiguous.')
    return values[0]


def libraries(home):
    roots = [home / '.local/share/Steam', home / '.steam/steam', home / '.steam/root']
    found = []
    for root in roots:
        if root.is_dir() and root.resolve() not in found:
            found.append(root.resolve())
    for root in list(found):
        try:
            text = metadata(root / 'steamapps/libraryfolders.vdf')
            for key, value in pairs(text):
                if key == 'path' or key.isdigit():
                    path = Path(value)
                    if path.is_absolute() and (path / 'steamapps').is_dir() and path.resolve() not in found:
                        found.append(path.resolve())
        except (OSError, UnicodeError, IntakeError):
            pass
    return found


def discover(home):
    candidates = []
    for library in libraries(home):
        manifest = library / ('steamapps/appmanifest_' + APPID + '.acf')
        try:
            text = metadata(manifest)
            if scalar(text, 'appid') != APPID:
                continue
            name = scalar(text, 'installdir')
            if name in ('.', '..') or '/' in name or '\\' in name:
                continue
            game = library / 'steamapps/common' / name
            if (game / 'Data').is_dir():
                candidates.append((game, manifest))
        except (OSError, UnicodeError, IntakeError):
            pass
    return candidates


def collect(game, manifest=None):
    """Only Data/*.pak and Data/Localization/*.pak. No saves, userdata or Mods scan."""
    root = game.resolve(strict=True)
    data = root / 'Data'
    if data.is_symlink() or not data.is_dir():
        raise IntakeError('Choose the installed BG3 folder containing a real Data directory.')
    build = None
    if manifest:
        text = metadata(manifest)
        if scalar(text, 'appid') != APPID:
            raise IntakeError('Steam application mismatch.')
        value = scalar(text, 'buildid')
        if not re.fullmatch(r'[0-9]{1,12}', value):
            raise IntakeError('Invalid Steam build identifier.')
        build = value
    paths = []
    locations = [data]
    locale = data / 'Localization'
    if locale.is_dir() and not locale.is_symlink():
        locations.append(locale)
    for location in locations:
        with os.scandir(location) as entries:
            for entry in entries:
                if entry.name.lower().endswith('.pak'):
                    if len(paths) >= MAX_ARCHIVES:
                        raise IntakeError('Archive-count limit exceeded.')
                    paths.append(Path(entry.path))
    rows, skipped = [], 0
    index_read_budget = [256 * 1024 * 1024, time.monotonic() + 120]
    for ordinal, path in enumerate(sorted(paths), 1):
        print("Inspecting archive " + str(ordinal) + " of " + str(len(paths)) + "...", flush=True)
        try:
            # Parent locations are fixed and not links; final component is opened O_NOFOLLOW.
            head, size = regular_bytes(path, HEADER_LIMIT)
        except (OSError, IntakeError):
            skipped += 1
            continue
        recognized = bool(KNOWN_NAME.fullmatch(path.name)) and not re.search(r'\d{12,}', path.name)
        signature = 'LSPK' if head[:4] == b'LSPK' else 'unrecognized'
        version = int.from_bytes(head[4:8], 'little') if signature == 'LSPK' and len(head) >= 8 else None
        rows.append(dict(label=path.name if recognized else 'unrecognized-archive-' + str(len(rows) + 1),
                         location='Localization' if path.parent == locale else 'Data',
                         size_bytes=size, header_bytes_read=len(head),
                         header_sha256=hashlib.sha256(head).hexdigest(),
                         signature=signature, header_version_candidate=version,
                         index=safe_inspect(path, index_read_budget) if signature == 'LSPK' and version == 18 else dict(status='unresolved', reason='not_lspk_v18')))
    if not rows:
        raise IntakeError('No readable archive files found in Data or Localization.')
    return dict(schema='retrofy-bg3-index-v2', appid=APPID, steam_build_id=build,
                fingerprint_scope='metadata, partial archive headers and decoded index digests; NOT full-file verification',
                indexed_archives=sum(row['index']['status'] == 'indexed' for row in rows),
                index_bytes_read=256 * 1024 * 1024 - index_read_budget[0],
                aggregate_categories=aggregate(rows),
                archives=rows, skipped_archive_entries=skipped,
                total_archive_bytes=sum(row['size_bytes'] for row in rows),
                privacy=dict(account_ids_included=False, absolute_paths_included=False,
                             saves_read=False, game_contents_extracted=False, network_used=False),
                limitations=['Build ID is metadata, not proof of unmodified files.',
                             'Archive header hashes are partial fingerprints, not full file hashes.',
                             'Only version-18 directory indexes are decoded; no payloads or scripts are read/executed.',
                             'Categories are filename-based hypotheses, not recovered semantics.',
                             'Totals count physical index records; patch overlays and dependencies are unresolved.',
                             'Limits: 32 MiB compressed/128 MiB decoded per index, 256 MiB index reads per run, 45 seconds per index / 120 seconds total parser work; blocking filesystem I/O is not timed out.',
                             'Mods, loose overrides, permissions, adaptation rights and compatibility are unassessed.'])


def aggregate(rows):
    totals = {key: dict(entries=0, stored_bytes=0, logical_bytes=0) for key in CATEGORIES}
    for row in rows:
        if row['index']['status'] != 'indexed':
            continue
        for key, values in row['index']['categories'].items():
            for field, value in values.items():
                totals[key][field] += value
    return totals


def summary_text(report):
    lines = ['RETROFY BG3 INDEX ANALYSIS v2', 'Nothing uploaded. No payloads extracted.',
             'Steam build: ' + (report['steam_build_id'] or 'not identified'),
             'Archive headers inspected: ' + str(len(report['archives'])),
             'Indexes decoded: ' + str(report['indexed_archives']),
             'Unresolved archives: ' + str(len(report['archives']) - report['indexed_archives']),
             '', 'Candidate entries (filename heuristics):']
    for name in CATEGORIES:
        values = report['aggregate_categories'][name]
        if values['entries']:
            lines.append(name + ': ' + str(values['entries']) + ' / ' + str(values['logical_bytes']) + ' logical bytes')
    lines += ['', 'Physical records only. Patches/duplicates not resolved.',
              'These bytes are NOT a GBC ROM-size requirement.',
              'Rules, dependencies, fidelity and compatibility remain unproved.',
              'Full details and failure reasons: report.json']
    return '\n'.join(lines) + '\n'


def save_report(report, parent):
    parent.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='Retrofy-Report-', dir=parent))
    os.chmod(folder, 0o700)
    path = folder / 'report.json'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    summary = folder / 'SUMMARY.txt'
    fd = os.open(summary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(summary_text(report))
    return path


class Dialog:
    def __init__(self):
        self.kind = 'kdialog' if shutil.which('kdialog') else 'zenity' if shutil.which('zenity') else None
        if not self.kind:
            raise IntakeError('KDialog or Zenity is required for the graphical intake. No software was installed.')

    def run(self, mode, text):
        if self.kind == 'kdialog':
            flag = {'ask': '--yesno', 'info': '--msgbox', 'folder': '--getexistingdirectory'}[mode]
            args = ['kdialog', '--title', 'Retrofy local intake', flag, text]
        elif mode == 'folder':
            args = ['zenity', '--file-selection', '--directory', '--title=Choose the Baldurs Gate 3 folder']
        else:
            args = ['zenity', '--title=Retrofy local intake', '--question' if mode == 'ask' else '--info', '--text=' + text, '--width=640']
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout.strip()


def main():
    dialog = None
    try:
        dialog = Dialog()
        status, _ = dialog.run('ask', 'Inspect your installed Baldurs Gate 3?\n\nReads installation metadata, 40-byte archive header probes and bounded LSPK v18 DIRECTORY INDEXES. Indexes are decompressed in memory; entry payloads are never extracted or decoded. Creates a NEW private report folder on your Desktop.\n\nNo account IDs in the report. No saves read, game extraction, network use, installation changes or automatic upload.\n\nThis is intake only, not a game converter. Continue?')
        if status:
            return 0
        home = Path.home()
        choices = discover(home)
        if len(choices) == 1:
            game, manifest = choices[0]
        else:
            dialog.run('info', 'Choose the installed Baldurs Gate 3 folder containing Data and bin.\n\nIf there are multiple Steam libraries, select the installation you want inspected.')
            status, selected = dialog.run('folder', str(home))
            if status or not selected:
                return 0
            game, manifest = Path(selected), None
            candidate = game.parent.parent / ('appmanifest_' + APPID + '.acf')
            if candidate.is_file() and not candidate.is_symlink():
                manifest = candidate
        report = collect(game, manifest)
        # Fixed standard Desktop if present; otherwise home. No account directory enumeration.
        parent = home / 'Desktop' if (home / 'Desktop').is_dir() else home
        path = save_report(report, parent)
        message = ('Index analysis complete: ' + str(report['indexed_archives']) + ' indexes decoded / ' + str(len(report['archives'])) + ' archives.\n\n'
                   'Steam build: ' + (report['steam_build_id'] or 'not identified') + '\n'
                   'A NEW Retrofy-Report folder was created on your Desktop (or home folder).\n'
                   'Open SUMMARY.txt for the short result, or report.json for details. Nothing was uploaded.\n\n'
                   'No conversion or compatibility claim is made.')
        print(message)
        dialog.run('info', message)
        # Explicit local file-manager target only, no URLs or report contents sent elsewhere.
        if shutil.which('dolphin'):
            subprocess.Popen(['dolphin', str(path.parent)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 0
    except (OSError, UnicodeError, IntakeError):
        safe = 'Intake could not finish. No installation files were changed or uploaded. Check that BG3 is installed and the Data folder is readable. A partial new report folder may remain if writing failed.'
        print(safe)
        if dialog:
            dialog.run('info', safe)
        return 1

if __name__ == '__main__':
    sys.exit(main())
