"""Exact host/native checks. No commercial material or external services."""
import ctypes
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from experiment import CODECS, CORPORA, PREVIOUS, corpus, digest

spec = importlib.util.spec_from_file_location('previous_check', PREVIOUS / 'check.py')
previous = importlib.util.module_from_spec(spec)
# Prior check.py imports a same-named experiment; select it explicitly.
own_experiment = sys.modules['experiment']
del sys.modules['experiment']
sys.path.insert(0, str(PREVIOUS))
try:
    spec.loader.exec_module(previous)
finally:
    sys.path.pop(0)
    sys.modules['experiment'] = own_experiment

TRAITS = previous.TRAITS


def reference(scenes, room, traits, flags, key, tokens):
    out = [[128, 144, 145, 146, 147][v] for v in scenes[room]]
    border = 143 if (tokens[1] - 4) & 1 else 129
    for y in range(2, 17):
        out[y * 20] = out[y * 20 + 19] = border
    for x in range(20):
        out[40 + x] = out[320 + x] = border
    for x in range(1, 19):
        out[200 + x] = 130 if tokens[2] == 9 else 128
    for offset in (160, 179, 50, 330):
        out[offset] = 128
    for offset, value in ((125, 133 if tokens[4] == 13 else 132),
                          (173, 134 if tokens[5] == 15 else 135),
                          (209, 131 if tokens[3] == 11 else 141),
                          (178, 136 if tokens[6] == 17 else 137),
                          (269, 138 if tokens[7] == 19 else 142)):
        out[offset] = value
    return out


def host(folder, scenes):
    library = folder / 'host.dylib'
    subprocess.run(['cc', '-std=c99', '-shared', '-fPIC', '-O2', '-DUSE_MODEL=0',
                    str(folder / 'codec.c'), str(folder / 'engine.c'), '-o', str(library)],
                   check=True, capture_output=True)
    dll = ctypes.CDLL(str(library))
    output = (ctypes.c_uint8 * 360).in_dll(dll, 'screen_map')
    exact = overlays = 0
    for room, scene in enumerate(scenes):
        dll.decode_scene(room, output)
        assert list(output) == [[128, 144, 145, 146, 147][v] for v in scene]
        assert ctypes.c_uint8.in_dll(dll, 'codec_error').value == 0
        exact += 1
        for flags in range(16):
            for key in range(2):
                dll.decode_scene(room, output)
                dll.generate(TRAITS[room], flags, key)
                dll.render(TRAITS[room], flags, key)
                assert list(output) == reference(scenes, room, TRAITS[room], flags, key,
                                                 previous.teacher(TRAITS[room], flags, key))
                overlays += 1
    return dict(exact_unoverlaid_scenes=exact, exact_overlay_contexts=overlays,
                tile_comparisons=(exact + overlays) * 360)


def check(build, out):
    out.mkdir(parents=True, exist_ok=False)
    result = dict(schema=1, scope='Exact synthetic content and inherited state tests', corpora={})
    for name in CORPORA:
        scenes = corpus(name)
        variants = result['corpora'][name] = {}
        for codec in CODECS:
            folder = build / name / codec
            target = out / name / codec
            target.mkdir(parents=True)
            host_result = host(folder, scenes)
            video = dict(vram_scenes=0, sampled_lcd_frames=0, dma_start_lines=[], dma_end_lines=[])
            def frame_observer(p, symbols):
                if p.memory[symbols['_ready']]:
                    assert p.memory[0xff40] & 128, 'LCD disabled after startup'
                    video['sampled_lcd_frames'] += 1
            def scene_observer(p, symbols, label):
                def value(name):
                    return p.memory[symbols['_' + name]]
                assert value('codec_error') == 0 and value('dma_error') == 0
                assert 144 <= value('dma_start_ly') <= value('dma_end_ly') <= 153
                video['dma_start_lines'].append(value('dma_start_ly'))
                video['dma_end_lines'].append(value('dma_end_ly'))
                room, key = value('room'), value('key')
                flags = p.memory[symbols['_flags'] + room]
                wanted = reference(scenes, room, TRAITS[room], flags, key,
                                   previous.teacher(TRAITS[room], flags, key))
                font = [p.memory[symbols['_font_tiles'] + i] for i in range(59)]
                text = {0: f'R{room:02d} A:USE B:INFO',
                        1: f'KEY:{key} QUEST:{int(bool(flags & 4))}',
                        17: 'CHEST NPC TORCH FLAG' if value('info') else 'DPAD MOVE 32 ROOMS'}
                for y in range(18):
                    row = wanted[y * 20:(y + 1) * 20]
                    if y in text:
                        row = [font[ord(c) - 32] for c in text[y].ljust(20)]
                    if y == value('py'):
                        row[value('px')] = 139
                    assert [p.memory[0x9800 + y * 32 + x] for x in range(20)] == row, (label, y, 'VRAM')
                video['vram_scenes'] += 1
            # Reuse the frozen controller replay/state suite with only the
            # independent content renderer replaced. Alias selects exact facts.
            with tempfile.TemporaryDirectory(prefix='retrofy-content-') as temporary:
                alias = Path(temporary)
                (alias / 'procedural').symlink_to(folder, target_is_directory=True)
                native = previous.emulated(alias, 'procedural', target / 'emulator',
                    scene_reference=lambda room, t, f, k, tokens: reference(scenes, room, t, f, k, tokens),
                    scene_observer=scene_observer, frame_observer=frame_observer)
            native['variant'] = codec
            native['limits'].append('Visual corpus is original synthetic; content fidelity is tile-ID exactness only.')
            video['dma_start_lines'] = [min(video['dma_start_lines']), max(video['dma_start_lines'])]
            video['dma_end_lines'] = [min(video['dma_end_lines']), max(video['dma_end_lines'])]
            native['video'] = video
            # Overflow invalidates cycle estimates, not separate exactness.
            variants[codec] = dict(host=host_result, native=native)
            (target / 'checks.json').write_text(json.dumps(variants[codec], indent=2) + '\n')
            print(name, codec, 'checked', native['input_to_scene_frames'],
                  native['stage_timer_ticks_1024_tcycles']['render'], flush=True)
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
