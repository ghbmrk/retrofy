"""One bounded loop: frozen data, build, exact checks, repeat, selection.
Run with a Python environment containing PyBoy 2.7.0 and Pillow.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from experiment import build, CORPORA, CODECS
from properties import check as properties
from summarize import summarize


def run(out, lcc):
    out.mkdir(parents=True, exist_ok=False)
    build(out / 'build', lcc)
    (out / 'properties.json').write_text(json.dumps(properties(), indent=2) + '\n')
    subprocess.run([sys.executable, str(Path(__file__).with_name('check.py')),
                    str(out / 'build'), str(out / 'checks')], check=True, timeout=600)
    build(out / 'repeat', lcc)
    first = json.loads((out / 'build' / 'builds.json').read_text())
    second = json.loads((out / 'repeat' / 'builds.json').read_text())
    repeats = {}
    for name in CORPORA:
        repeats[name] = {}
        for codec in CODECS:
            a = first['corpora'][name]['variants'][codec]['rom_sha256']
            b = second['corpora'][name]['variants'][codec]['rom_sha256']
            assert a == b, (name, codec, 'Non-reproducible ROM')
            repeats[name][codec] = a
    (out / 'reproducibility.json').write_text(json.dumps(repeats, indent=2) + '\n')
    result = summarize(out / 'build', out / 'checks')
    (out / 'selection.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({name: dict(selected=item['selected'], frontier=item['frontier'])
                      for name, item in result['corpora'].items()}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--lcc', required=True)
    args = parser.parse_args()
    run(args.out.resolve(), args.lcc)
