import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_intake', ROOT / 'intake/intake.py')
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()
        self.library = self.home / '.local/share/Steam'
        self.game = self.library / 'steamapps/common/Baldurs Gate 3'
        (self.game / 'Data/Localization').mkdir(parents=True)
        self.manifest = self.library / 'steamapps/appmanifest_1086940.acf'
        self.manifest.write_text('"AppState" { "appid" "1086940" "installdir" "Baldurs Gate 3" "buildid" "12345" "LastOwner" "PRIVATE-OWNER-SENTINEL" }')
        (self.game / 'Data/Game.pak').write_bytes(b'LSPK' + (18).to_bytes(4,'little') + b'x'*10000)
    def tearDown(self):
        self.tmp.cleanup()
    def test_discovery_and_whitelisted_report(self):
        found = intake.discover(self.home)
        self.assertEqual(found,[(self.game,self.manifest)])
        report=intake.collect(*found[0]); text=json.dumps(report)
        self.assertEqual(report['steam_build_id'],'12345')
        self.assertEqual(report['archives'][0]['header_bytes_read'],40)
        self.assertEqual(report['archives'][0]['signature'],'LSPK')
        self.assertNotIn('PRIVATE-OWNER-SENTINEL',text)
        self.assertNotIn(str(self.home),text)
        self.assertEqual(report['archives'][0]['header_sha256'],hashlib.sha256((self.game/'Data/Game.pak').read_bytes()[:40]).hexdigest())
    def test_secondary_library(self):
        other=self.home/'external volume';(other/'steamapps').mkdir(parents=True)
        (self.library/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "1" { "path" "'+str(other)+'" } }')
        self.assertIn(other,intake.libraries(self.home))
    def test_no_saves_recursion_or_arbitrary_labels(self):
        (self.game/'Data/Saves').mkdir();(self.game/'Data/Saves/Private.pak').write_bytes(b'secret')
        (self.game/'Data/private-owner.pak').write_bytes(b'not-lspk')
        (self.game/'Data/Localization/English.pak').write_bytes(b'LSPK')
        r=intake.collect(self.game,self.manifest)
        self.assertEqual(len(r['archives']),3)
        self.assertNotIn('private-owner',json.dumps(r))
        self.assertNotIn('Private.pak',json.dumps(r))
    def test_links_and_devices_are_not_read(self):
        private=self.home/'private.txt';private.write_text('must not read')
        (self.game/'Data/Linked.pak').symlink_to(private)
        os.mkfifo(self.game/'Data/Pipe.pak')
        r=intake.collect(self.game,self.manifest)
        self.assertEqual(len(r['archives']),1)
        self.assertEqual(r['skipped_archive_entries'],2)
    def test_data_directory_links_refused(self):
        other=self.home/'other';other.mkdir()
        (self.game/'Data/Game.pak').unlink();(self.game/'Data/Localization').rmdir();(self.game/'Data').rmdir()
        (self.game/'Data').symlink_to(other)
        with self.assertRaises(intake.IntakeError):intake.collect(self.game)
    def test_metadata_limits_and_wrong_app(self):
        self.manifest.write_text('x'*(intake.MAX_METADATA+1))
        with self.assertRaises(intake.IntakeError):intake.collect(self.game,self.manifest)
        self.manifest.write_text('"appid" "999" "buildid" "1"')
        with self.assertRaises(intake.IntakeError):intake.collect(self.game,self.manifest)
    def test_non_destructive_private_reports(self):
        before=(self.game/'Data/Game.pak').read_bytes()
        r=intake.collect(self.game,self.manifest)
        one=intake.save_report(r,self.home/'Desktop');two=intake.save_report(r,self.home/'Desktop')
        self.assertNotEqual(one,two)
        self.assertEqual(stat.S_IMODE(one.stat().st_mode),0o600)
        self.assertEqual(stat.S_IMODE(one.parent.stat().st_mode),0o700)
        self.assertEqual(before,(self.game/'Data/Game.pak').read_bytes())
    def test_cancel_creates_no_report(self):
        class Cancel:
            def run(self,*args):return 1,''
        with patch.object(intake,'Dialog',return_value=Cancel()),patch.object(intake,'save_report') as write:
            self.assertEqual(intake.main(),0);write.assert_not_called()
    def test_bundle_members_permissions_and_launcher_arguments(self):
        blob=json.loads((ROOT/'worker/intake-bundle.js').read_text().split('=',1)[1].rstrip(';\n '))
        packed=base64.b64decode(blob['base64'])
        self.assertEqual(hashlib.sha256(packed).hexdigest(),blob['sha256'])
        with tarfile.open(fileobj=io.BytesIO(packed),mode='r:gz') as tar:
            self.assertEqual(len(tar.getmembers()),6)
            for member in tar.getmembers():
                self.assertTrue(member.isfile());self.assertTrue(member.name.startswith('Retrofy-BG3-Index-v2/'))
                self.assertNotIn('..',member.name)
                name=Path(member.name).name
                self.assertEqual(tar.extractfile(member).read(),(ROOT/'intake'/name).read_bytes())
            self.assertEqual(tar.getmember('Retrofy-BG3-Index-v2/Retrofy-Intake.desktop').mode,0o755)
        line=next(x[5:] for x in (ROOT/'intake/Retrofy-Intake.desktop').read_text().splitlines() if x.startswith('Exec='))
        args=shlex.split(line);self.assertEqual(args[:2],['python3','-c']);self.assertEqual(args[-1],'%k')
        compile(args[2],'<desktop-launcher>','exec')

if __name__=='__main__':unittest.main()
