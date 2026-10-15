"""Build a deterministic source-only download; no user files or dependencies."""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
buffer = io.BytesIO()
with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
    for name in ['README.txt', 'Retrofy-Intake.desktop', 'Retrofy-Intake.sh', 'intake.py']:
        data = (root / 'intake' / name).read_bytes()
        info = tarfile.TarInfo('Retrofy-Intake/' + name)
        info.size = len(data)
        info.mode = 0o755 if name.endswith(('.sh', '.desktop')) else 0o644
        info.uid = info.gid = info.mtime = 0
        info.uname = info.gname = ''
        archive.addfile(info, io.BytesIO(data))
packed = gzip.compress(buffer.getvalue(), mtime=0)
meta = dict(version='1.0.0', filename='Retrofy-Intake-SteamOS.tar.gz', bytes=len(packed),
            sha256=hashlib.sha256(packed).hexdigest(), base64=base64.b64encode(packed).decode())
(root / 'worker/intake-bundle.js').write_text('export const INTAKE = ' + json.dumps(meta) + ';\n')
print('Packaged local intake:', len(packed), 'bytes; SHA-256', meta['sha256'])
