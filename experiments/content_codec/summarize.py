"""Select a measured representation frontier, never an adaptation-success label."""
import json
from pathlib import Path
import sys


def summarize(build, checks):
    builds = json.loads((build / 'builds.json').read_text())
    results = json.loads((checks / 'results.json').read_text())
    report = dict(schema=1, status='synthetic_representation_evidence_only',
                  budgets=dict(full_scene_frames=4, cached_update_frames=2), corpora={})
    for name, corpus in builds['corpora'].items():
        variants = {}
        for codec, data in corpus['variants'].items():
            native = results['corpora'][name][codec]['native']
            assert native['rom_sha256'] == data['rom_sha256']
            groups = native['input_to_scene_groups']
            exact = (native['scene_checks'] == 1028 and native['video']['vram_scenes'] == 1028)
            timers_valid = all(m['overflows'] == 0 for m in native['stage_timer_ticks_1024_tcycles'].values())
            gate = (exact and timers_valid and groups['full']['max'] <= 4 and groups['cached']['max'] <= 2)
            variants[codec] = dict(linked_rom_extent_bytes=native['linker']['linked_rom_extent_bytes'],
                                   data_bytes=data['data_bytes'], heldout_payload_bytes=data['heldout_payload_bytes'],
                                   full_frames=groups['full']['max'], cached_frames=groups['cached']['max'],
                                   measured_gate_pass=gate)
        eligible = {k: v for k, v in variants.items() if v['measured_gate_pass']}
        selected = min(eligible, key=lambda k: eligible[k]['linked_rom_extent_bytes']) if eligible else None
        frontier = []
        for key, value in eligible.items():
            dominated = any(other != key
                            and candidate['linked_rom_extent_bytes'] <= value['linked_rom_extent_bytes']
                            and candidate['full_frames'] <= value['full_frames']
                            and (candidate['linked_rom_extent_bytes'] < value['linked_rom_extent_bytes']
                                 or candidate['full_frames'] < value['full_frames'])
                            for other, candidate in eligible.items())
            if not dominated:
                frontier.append(key)
        report['corpora'][name] = dict(selected=selected, frontier=frontier, variants=variants)
    report['unresolved'] = ['Real-game behavior and asset recovery', 'Delayed cross-room causal dependencies beyond the inherited kernel',
                            'Human readability/feel', 'Independent evaluation', 'Physical Chromatic execution',
                            'Banked large-world scalability', 'Audio and battery saves', 'Stack high-water']
    return report


if __name__ == '__main__':
    print(json.dumps(summarize(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
