"""Build only repository-authored fixtures. Never approves third-party input."""
import json
from pathlib import Path
import subprocess
import sys
from retrofy.core import canonical,digest
from retrofy.cli import plan
root=Path(sys.argv[1]); lcc=sys.argv[2]; root.mkdir(parents=True,exist_ok=False)
reference=json.loads(Path('evaluation/summary.json').read_text())
rights=root/'rights.json'
rights.write_text(json.dumps(dict(access_basis='MIT synthetic fixtures',adaptation_basis='MIT',redistribution='MIT fixture artifacts only')))
for name in ('push','interactions','max-board','crowded'):
    path=Path('fixtures')/(name+'.xsb')
    data=path.read_bytes()
    if digest(data)!=reference['fixtures'][name]['input_sha256']:
        raise SystemExit('Fixture changed: refuse automatic rights/plan approval')
    p=plan(data); target=root/(name+'-plan.json'); target.write_bytes(canonical(p))
    assert p['report']['decision']=='eligible-for-declared-demake'
    subprocess.run([sys.executable,'-m','retrofy.cli','build',str(path),'--plan',str(target),'--approve',digest(canonical(p)),
                    '--rights',str(rights),'--out',str(root/name),'--lcc',lcc],check=True)
