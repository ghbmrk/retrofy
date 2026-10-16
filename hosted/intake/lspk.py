"""Bounded LSPK v18 index-only reader. Independently implemented from public layouts.
References: Norbyte/lslib PackageFormat.cs + PackageReader.cs at
6f5f6987d10d8485876b8368431c948e4dea4f83; lz4/lz4 doc/lz4_Block_format.md.
No directory-referenced payload is read, decompressed, executed, extracted, or returned.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import time

HEADER = struct.Struct('<4sIQIBB16sH')
ENTRY = struct.Struct('<256sIHBBII')
MAX_INDEX_BYTES = 32 * 1024 * 1024
MAX_DECODED_BYTES = 128 * 1024 * 1024
MAX_FILES = 400000
MAX_SECONDS = 45
METHODS = {0: 'none', 1: 'zlib', 2: 'lz4', 3: 'zstd'}
CATEGORIES = ('rules_candidate', 'story_script_candidate', 'dialogue_candidate',
              'localization_candidate', 'structured_data', 'texture', 'audio',
              'video', 'geometry_animation', 'shader', 'other')

class IndexFailure(Exception):
    """Only fixed error codes may reach the report; never filenames/contents."""
    pass


def fail(code):
    raise IndexFailure(code)


def lz4_block(data, expected, deadline=None):
    if not 0 <= expected <= MAX_DECODED_BYTES or len(data) > MAX_INDEX_BYTES:
        fail('index_resource_limit')
    out = bytearray()
    pos = 0
    def length(base):
        nonlocal pos
        if base == 15:
            while True:
                if pos >= len(data):
                    fail('truncated_lz4_length')
                extra = data[pos]; pos += 1; base += extra
                if base > expected:
                    fail('lz4_output_limit')
                if extra != 255:
                    break
        return base
    while pos < len(data):
        if deadline is not None and time.monotonic() > deadline:
            fail('index_time_limit')
        token = data[pos]; pos += 1
        literals = length(token >> 4)
        if pos + literals > len(data) or len(out) + literals > expected:
            fail('invalid_lz4_literals')
        out.extend(data[pos:pos+literals]); pos += literals
        if pos == len(data):
            if len(out) != expected:
                fail('lz4_size_mismatch')
            return out
        if pos + 2 > len(data):
            fail('truncated_lz4_offset')
        offset = data[pos] | (data[pos+1] << 8); pos += 2
        if offset == 0 or offset > len(out):
            fail('invalid_lz4_offset')
        matched = length(token & 15) + 4
        if len(out) + matched > expected:
            fail('lz4_output_limit')
        # Match overlap repeats prior bytes. Work in bounded chunks, not byte-at-a-time.
        remaining = matched
        while remaining:
            amount = min(remaining, 65536)
            pattern = bytes(out[-offset:])
            out.extend((pattern * ((amount + offset - 1) // offset))[:amount])
            remaining -= amount
            if deadline is not None and time.monotonic() > deadline:
                fail('index_time_limit')
    fail('truncated_lz4_block')


def category(name):
    name = name.lower()
    ext = PurePosixPath(name).suffix
    if '/stats/' in '/' + name and ext in ('.txt', '.lsx', '.lsf', '.lsj'):
        return 'rules_candidate'
    if '/dialogs/' in '/' + name or '/dialogues/' in '/' + name:
        return 'dialogue_candidate'
    if ext in ('.osi', '.lua', '.story', '.goal') or '/story/' in '/' + name or '/scripts/' in '/' + name:
        return 'story_script_candidate'
    if ext in ('.loca', '.loc'):
        return 'localization_candidate'
    if ext in ('.lsx', '.lsf', '.lsj', '.lsb'):
        return 'structured_data'
    if ext in ('.dds', '.png', '.gtp', '.gts', '.tga', '.jpg'):
        return 'texture'
    if ext in ('.wem', '.bnk', '.wav', '.ogg', '.mp3'):
        return 'audio'
    if ext in ('.bk2', '.bik', '.webm', '.mp4'):
        return 'video'
    if ext in ('.gr2', '.gltf', '.glb', '.dae', '.lsm'):
        return 'geometry_animation'
    if '/shaders/' in '/' + name or ext in ('.hlsl', '.spv', '.dxil'):
        return 'shader'
    return 'other'


def open_regular(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    stream = os.fdopen(fd, 'rb')
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        stream.close(); fail('non_regular_archive')
    return stream


def read_at(stream, offset, size, file_size):
    if offset < 0 or size < 0 or offset + size > file_size:
        fail('index_out_of_bounds')
    stream.seek(offset)
    data = stream.read(size)
    if len(data) != size:
        fail('archive_changed_or_truncated')
    return data


def inspect(path, read_budget=None):
    """Aggregate physical directory records only. Names remain transient in RAM."""
    path = Path(path)
    deadline = time.monotonic() + MAX_SECONDS
    if read_budget is not None and len(read_budget) > 1:
        deadline = min(deadline, read_budget[1])
    def read(stream, offset, size, file_size):
        if time.monotonic() > deadline:
            fail('index_time_limit')
        if read_budget is not None:
            if size > read_budget[0]:
                fail('session_read_limit')
            read_budget[0] -= size
        return read_at(stream, offset, size, file_size)
    with open_regular(path) as stream:
        before = os.fstat(stream.fileno())
        header = read(stream, 0, HEADER.size, before.st_size)
        magic, version, index_offset, index_size, flags, priority, _, parts = HEADER.unpack(header)
        if magic != b'LSPK' or version != 18:
            fail('unsupported_format_requires_lspk_v18')
        if not 1 <= parts <= 256:
            fail('invalid_part_count')
        # Solid payload layouts need a separate interpretation; do not guess costs/bounds.
        if flags & ~14:
            fail('unknown_package_flags')
        if flags & 4:
            fail('solid_archive_not_supported')
        if index_offset < HEADER.size or index_size < 8 or index_size > MAX_INDEX_BYTES + 8:
            fail('invalid_index_bounds_or_limit')
        preamble = read(stream, index_offset, 8, before.st_size)
        count, packed_size = struct.unpack('<II', preamble)
        if count > MAX_FILES or count * ENTRY.size > MAX_DECODED_BYTES or packed_size > MAX_INDEX_BYTES:
            fail('index_resource_limit')
        if index_size != packed_size + 8:
            fail('inconsistent_index_size')
        compressed = read(stream, index_offset+8, packed_size, before.st_size)
        decoded = lz4_block(compressed, count * ENTRY.size, deadline)
        del compressed
        # Only file sizes of referenced parts are inspected, never their payloads.
        part_sizes = {0: before.st_size}
        bins = {name: dict(entries=0, stored_bytes=0, logical_bytes=0) for name in CATEGORIES}
        methods = {v: 0 for v in METHODS.values()}
        seen_names, seen_regions = set(), set()
        duplicate_paths, shared_regions, shared_region_bytes = 0, 0, 0
        for index in range(count):
            if time.monotonic() > deadline:
                fail('index_time_limit')
            name_bytes, offset_low, offset_high, part, compression, stored, unpacked = ENTRY.unpack_from(decoded, index * ENTRY.size)
            if b'\0' not in name_bytes:
                fail('unterminated_entry_name')
            try:
                name = name_bytes.split(b'\0', 1)[0].decode('utf-8').replace('\\', '/')
            except UnicodeError:
                fail('invalid_entry_name_encoding')
            if not name or name.startswith('/') or ':' in name or any(p in ('.', '..', '') for p in name.split('/')) or any(ord(c) < 32 for c in name):
                fail('unsafe_entry_name')
            if part >= parts or compression & 15 not in METHODS:
                fail('unsupported_entry_flags_or_part')
            if part not in part_sizes:
                part_path = path.with_name(path.stem + '_' + str(part) + path.suffix)
                try:
                    with open_regular(part_path) as part_stream:
                        part_sizes[part] = os.fstat(part_stream.fileno()).st_size
                except OSError:
                    fail('missing_or_unreadable_archive_part')
            offset = offset_low | (offset_high << 32)
            if offset + stored > part_sizes[part]:
                fail('entry_payload_out_of_bounds')
            if part == 0 and stored and (offset < HEADER.size or (offset < index_offset+index_size and offset+stored > index_offset)):
                fail('entry_overlaps_metadata')
            method = compression & 15
            if method == 0 and unpacked not in (0, stored):
                fail('inconsistent_uncompressed_entry')
            logical = unpacked if method else stored
            if stored and method and not logical:
                fail('inconsistent_compressed_entry')
            key = hashlib.sha256(name.encode()).digest()
            duplicate_paths += key in seen_names
            seen_names.add(key)
            region = part, offset, stored, logical, method
            if stored and region in seen_regions:
                shared_regions += 1; shared_region_bytes += stored
            seen_regions.add(region)
            bucket = bins[category(name)]
            bucket['entries'] += 1; bucket['stored_bytes'] += stored; bucket['logical_bytes'] += logical
            methods[METHODS[method]] += 1
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            fail('archive_changed_during_scan')
        return dict(status='indexed', format='LSPK-v18', entries=count, parts=parts,
                    priority_hint=priority, index_stored_bytes=index_size,
                    index_decoded_bytes=len(decoded), index_sha256=hashlib.sha256(decoded).hexdigest(),
                    file_bytes_read=HEADER.size + 8 + packed_size,
                    compression_methods=methods, categories=bins,
                    duplicate_path_records=duplicate_paths,
                    repeated_payload_regions=shared_regions,
                    repeated_region_reference_bytes=shared_region_bytes,
                    payload_read=False, overlay_resolved=False, semantics_recovered=False)


def safe_inspect(path, read_budget=None):
    try:
        return inspect(path, read_budget)
    except IndexFailure as error:
        return dict(status='unresolved', reason=str(error), semantics_recovered=False)
    except OSError:
        return dict(status='unresolved', reason='io_error_or_symlink', semantics_recovered=False)
    except (ValueError, struct.error):
        return dict(status='unresolved', reason='malformed_index', semantics_recovered=False)
