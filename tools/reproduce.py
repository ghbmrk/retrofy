"""Rebuild public synthetic fixtures, compare published ROM hashes, execute ROMs.
Use an environment with PyBoy 2.7.0/Pillow 12.3.0 and a C compiler.
python tools/reproduce.py NEW_OUTPUT_ROOT /path/to/gbdk/bin/lcc
"""
import json
import os
from pathlib import Path
import subprocess
import sys
root=Path(sys.argv[1]).resolve(); compiler=sys.argv[2]
if root.exists(): raise SystemExit('Output root must be unused')
root.mkdir(parents=True)
env=dict(os.environ,PYTHONPATH=str(Path.cwd()))
subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],check=True,env=env)
subprocess.run([sys.executable,'tools/build_fixtures.py',str(root/'builds'),compiler],check=True,env=env)
reference=json.loads(Path('evaluation/summary.json').read_text())
for name in ('push','interactions','max-board','crowded'):
    build=root/'builds'/name
    record=json.loads((build/'record.json').read_text())
    assert record['rom_sha256']==reference['fixtures'][name]['rom_sha256'],(name,'ROM differs; investigate toolchain/source change')
    subprocess.run([sys.executable,'tools/emulator_check.py',str(build),str(root/(name+'-checks'))],check=True,env=env)
print('Public fixture reproduction passed. No original-game or hardware claim established.')
