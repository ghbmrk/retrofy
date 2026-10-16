"""Frozen exact scene codecs, native costs, unseen content and entropy controls.

Original synthetic content only. No learned gameplay or commercial adaptation.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent / 'scene_tokens'
CODECS = ('raw', 'packed', 'rle', 'lz', 'patch', 'patch-fast')
CORPORA = ('shared', 'novel', 'entropy')
SPLIT = 24


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pack(values):
    value = bits = 0
    output = bytearray()
    for symbol in values:
        assert 0 <= symbol < 5
        value |= symbol << bits
        bits += 3
        while bits >= 8:
            output.append(value & 255)
            value >>= 8
            bits -= 8
    if bits:
        output.append(value)
    return bytes(output)


def unpack(data, count):
    value = bits = offset = 0
    result = []
    for _ in range(count):
        while bits < 3:
            value |= data[offset] << bits
            offset += 1
            bits += 8
        result.append(value & 7)
        value >>= 3
        bits -= 3
    return bytes(result)


def patches(scene):
    return [bytes(scene[(y + dy) * 20 + x + dx]
                  for dy in range(3) for dx in range(4))
            for y in range(0, 18, 3) for x in range(0, 20, 4)]


def unpatch(items):
    result = bytearray(360)
    for n, patch in enumerate(items):
        y, x = (n // 5) * 3, (n % 5) * 4
        for i, symbol in enumerate(patch):
            result[(y + i // 4) * 20 + x + i % 4] = symbol
    return bytes(result)


def corpus(name):
    # Equal training content for shared/novel. The held-out novel domain changes
    # the motif vocabulary, not just room IDs. Entropy has independent symbols.
    rng = random.Random(1729)
    motifs = [bytes(rng.randrange(5) for _ in range(12)) for _ in range(24)]
    output = []
    for room in range(32):
        local = random.Random(10000 + room)
        if name == 'entropy':
            scene = bytes(local.randrange(5) for _ in range(360))
        else:
            blocks = [motifs[local.randrange(len(motifs))] for _ in range(30)]
            # Two authored unique blocks per scene must survive exactly.
            for index in (room % 30, (room + 13) % 30):
                blocks[index] = bytes(local.randrange(5) for _ in range(12))
            if name == 'novel' and room >= SPLIT:
                blocks = [bytes(local.randrange(5) for _ in range(12)) for _ in range(30)]
            scene = unpatch(blocks)
        output.append(scene)
    return output


def dictionary(scenes):
    counts = Counter(p for scene in scenes[:SPLIT] for p in patches(scene))
    # Data-derived codebook, fitted only on frozen training scenes. No loss.
    return [p for p, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
            if count >= 2][:64]


def lz_encode(data):
    # Greedy bounded-window LZ: [literal count-1, bytes...] or
    # [0x80 | (match length-3), backward distance]. Overlap is allowed.
    result = bytearray()
    literal = bytearray()
    def flush():
        if literal:
            result.append(len(literal) - 1)
            result.extend(literal)
            literal.clear()
    position = 0
    while position < len(data):
        best_length = best_distance = 0
        for distance in range(1, min(position, 255) + 1):
            length = 0
            while (length < 130 and position + length < len(data)
                   and data[position + length] == data[position + length - distance]):
                length += 1
            if length > best_length:
                best_length, best_distance = length, distance
        if best_length >= 3:
            flush()
            result.extend((128 | (best_length - 3), best_distance))
            position += best_length
        else:
            literal.append(data[position])
            position += 1
            if len(literal) == 128:
                flush()
    flush()
    return bytes(result)


def encode(codec, scene, codebook):
    if codec == 'raw':
        return scene
    if codec == 'packed':
        return pack(scene)
    if codec == 'lz':
        return lz_encode(scene)
    if codec == 'rle':
        result = bytearray()
        position = 0
        while position < len(scene):
            end = position + 1
            while end < min(position + 32, len(scene)) and scene[end] == scene[position]:
                end += 1
            result.append((scene[position] << 5) | (end - position - 1))
            position = end
        return bytes(result)
    indexes = {p: i for i, p in enumerate(codebook)}
    result = bytearray()
    for patch in patches(scene):
        if patch in indexes:
            result.append(indexes[patch])
        else:
            result.append(255)
            result.extend(pack(patch))
    return bytes(result)


def decode(codec, data, codebook):
    if codec == 'raw':
        result = data
    elif codec == 'packed':
        result = unpack(data, 360)
    elif codec.startswith('patch'):
        items = []
        pos = 0
        for _ in range(30):
            token = data[pos]
            pos += 1
            if token == 255:
                items.append(unpack(data[pos:pos + 5], 12))
                pos += 5
            else:
                items.append(codebook[token])
        assert pos == len(data)
        result = unpatch(items)
    else:
        output = bytearray()
        pos = 0
        while pos < len(data):
            token = data[pos]
            pos += 1
            if codec == 'rle':
                output.extend([token >> 5] * ((token & 31) + 1))
            elif token & 128:
                distance = data[pos]
                pos += 1
                for _ in range((token & 127) + 3):
                    output.append(output[-distance])
            else:
                output.extend(data[pos:pos + token + 1])
                pos += token + 1
        result = bytes(output)
    assert len(result) == 360 and max(result) < 5
    return result


def c_array(name, values, ctype='uint8_t'):
    return 'const ' + ctype + ' ' + name + '[]={' + ','.join(map(str, values)) + '};\n'


def codec_header(codec, scenes):
    is_patch = codec.startswith('patch')
    codebook = dictionary(scenes) if is_patch else []
    streams = [encode(codec, scene, codebook) for scene in scenes]
    for scene, stream in zip(scenes, streams):
        assert decode(codec, stream, codebook) == scene
    offsets = [0]
    for stream in streams:
        offsets.append(offsets[-1] + len(stream))
    book = b''.join(pack(p) for p in codebook)
    if codec == 'patch-fast':
        book = bytes([128, 144, 145, 146, 147][v] for p in codebook for v in p)
    header = '#define CODEC ' + str(CODECS.index(codec)) + '\n'
    header += c_array('offsets', offsets, 'uint16_t')
    native_stream = b''.join(streams)
    if codec == 'raw':
        native_stream = bytes([128, 144, 145, 146, 147][v] for v in native_stream)
    header += c_array('payload', native_stream)
    if is_patch:
        header += c_array('codebook', book or b'\x00')
    return header, dict(payload_bytes=offsets[-1], index_bytes=66,
                        codebook_bytes=len(book) if book else int(is_patch),
                        training_payload_bytes=sum(map(len, streams[:SPLIT])),
                        heldout_payload_bytes=sum(map(len, streams[SPLIT:])),
                        codebook_entries=len(codebook), exact_host_scenes=32,
                        data_bytes=offsets[-1] + 66 + len(book) + int(is_patch and not book))


def run(command, cwd):
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        output, _ = process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        (cwd / 'build.log').write_text(output + '\nOwned compiler time limit exceeded.\n')
        raise RuntimeError('Compiler exceeded 120 seconds')
    (cwd / 'build.log').write_text(output)
    if process.returncode:
        raise RuntimeError('Build failed: ' + str(cwd / 'build.log'))


def build(out, lcc):
    out.mkdir(parents=True, exist_ok=False)
    report = dict(schema=1, seed=1729, lcc_sha256=digest(Path(lcc).read_bytes()), split=dict(training=list(range(24)), heldout=list(range(24, 32))),
                  scope='Original synthetic lossless visual content; no game recovery', corpora={})
    for name in CORPORA:
        scenes = corpus(name)
        report['corpora'][name] = dict(corpus_sha256=digest(b''.join(scenes)), variants={})
        for codec in CODECS:
            target = out / name / codec
            target.mkdir(parents=True)
            header, metrics = codec_header(codec, scenes)
            (target / 'content.h').write_text(header)
            for source in ('codec.c', 'codec.h', 'display.inc'):
                shutil.copyfile(ROOT / source, target / source)
            shutil.copyfile(PREVIOUS / 'engine.h', target / 'engine.h')
            # Reuse exact state mechanics and fact overlays, changing only decor.
            engine = (PREVIOUS / 'engine.c').read_text()
            begin = engine.index(' uint8_t x,y,theme=')
            end = engine.index(' for(x=1;x<19;', begin)
            engine = engine[:begin] + ''' uint8_t x,y,border=(tokens[1]&1)?143:129;
 (void)t;(void)f;(void)k;
 for(y=2;y<17;++y){screen_map[(uint16_t)y*20]=border;screen_map[(uint16_t)y*20+19]=border;}
 for(x=0;x<20;++x){screen_map[40+x]=border;screen_map[320+x]=border;}
''' + engine[end:]
            (target / 'engine.c').write_text(engine)
            # USE_MODEL=0 removes weights; frozen facts only.
            (target / 'model.h').write_text(c_array('traits', [((r * 13) ^ (r >> 1)) & 63 for r in range(32)]))
            main = (PREVIOUS / 'main.c').read_text()
            main = main.replace('#include "engine.h"', '#include "engine.h"\n#include "codec.h"\n#include <string.h>')
            main = main.replace('render(t,f,key);', 'decode_scene(room,screen_map);render(t,f,key);')
            main = main.replace('set_bkg_data(128,16,art);', 'set_bkg_data(128,16,art);set_bkg_data(144,4,decor);')
            # Four decorative patterns, separate from mechanical icons.
            art = [0, 0, 17, 17, 0, 0, 68, 68, 0, 0, 17, 17, 0, 0, 68, 68,
                   0, 0, 0, 0, 126, 126, 0, 0, 0, 0, 126, 126, 0, 0, 0, 0,
                   128, 128, 64, 64, 32, 32, 16, 16, 8, 8, 4, 4, 2, 2, 1, 1,
                   0, 0, 24, 24, 36, 36, 66, 66, 66, 66, 36, 36, 24, 24, 0, 0]
            main = main.replace('uint8_t adjacent', c_array('decor', art) + 'uint8_t adjacent')
            begin = main.index('void draw(void)')
            end = main.index('void act(void)', begin)
            main = main[:begin] + '#include "display.inc"\n' + main[end:]
            main = main.replace('draw();ready=1;', 'display_init();draw();ready=1;')
            (target / 'main.c').write_text(main)
            command = [lcc, '-msm83:gb', '-Wm-yC', '-Wm-yt0', '-Wm-yo2', '-Wm-ya0',
                       '-Wm-ynCONTENTCODEC', '-Wl-m', '-Wl-j', '-DUSE_MODEL=0',
                       '-o', 'scene.gbc', 'main.c', 'engine.c', 'codec.c']
            run(command, target)
            rom = (target / 'scene.gbc').read_bytes()
            assert len(rom) == 32768 and rom[0x147] == 0 and rom[0x143] == 192
            checksum = 0
            for b in rom[0x134:0x14d]:
                checksum = (checksum - b - 1) & 255
            assert checksum == rom[0x14d]
            metrics.update(rom_bytes=len(rom), rom_sha256=digest(rom),
                           source_sha256={p.name: digest(p.read_bytes()) for p in target.glob('*') if p.suffix in ('.c', '.h', '.inc')},
                           command=[Path(lcc).name] + command[1:])
            report['corpora'][name]['variants'][codec] = metrics
            print(name, codec, metrics['data_bytes'], flush=True)
    (out / 'builds.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--lcc', required=True)
    args = parser.parse_args()
    build(args.out.resolve(), args.lcc)
