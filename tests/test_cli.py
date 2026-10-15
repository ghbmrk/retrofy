import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from retrofy.core import canonical, digest, read_local, Rejected
from retrofy.cli import plan
ROOT=Path(__file__).resolve().parents[1]
class Intake(unittest.TestCase):
    def test_approval_and_rights_fail_closed_before_compiler(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); inp=root/'game.xsb'; inp.write_bytes((ROOT/'fixtures/push.xsb').read_bytes())
            p=plan(inp.read_bytes()); pf=root/'plan.json'; pf.write_bytes(canonical(p))
            rf=root/'rights.json'; rf.write_text('{}')
            base=[sys.executable,'-m','retrofy.cli','build',str(inp),'--plan',str(pf),
                  '--rights',str(rf),'--out',str(root/'output'),'--lcc','does-not-exist']
            r=subprocess.run(base+['--approve','wrong'],capture_output=True,text=True)
            self.assertEqual(r.returncode,2); self.assertIn('hash mismatch',r.stderr)
            r=subprocess.run(base+['--approve',digest(canonical(p))],capture_output=True,text=True)
            self.assertIn('Missing rights',r.stderr); self.assertFalse((root/'output').exists())
            inp.write_bytes((ROOT/'fixtures/interactions.xsb').read_bytes())
            r=subprocess.run(base+['--approve',digest(canonical(p))],capture_output=True,text=True)
            self.assertIn('Input/plan changed',r.stderr)
    def test_symlink_and_oversize(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); f=root/'large'; f.write_bytes(b'x'*65537)
            with self.assertRaises(Rejected): read_local(f)
            link=root/'link'; link.symlink_to(f)
            with self.assertRaises(Rejected): read_local(link)
