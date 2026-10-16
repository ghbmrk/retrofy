"""Original synthetic v18 fixtures; no shipped game archive is used."""
import ctypes
import ctypes.util
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('index_reader', ROOT/'intake/lspk.py')
lspk=importlib.util.module_from_spec(spec);spec.loader.exec_module(lspk)


def literal(data):
    output=bytearray([min(len(data),15)<<4])
    if len(data)>=15:
        remain=len(data)-15
        while remain>=255:
            output.append(255);remain-=255
        output.append(remain)
    return bytes(output)+data


def fixture(path,names=('Public/Shared/Stats/Generated/Data/Spell_Test.txt',), compression=0,parts=1,entry_part=0,solid=False):
    payload=b'ORIGINAL-FIXTURE-PAYLOAD-DO-NOT-READ'
    entry_rows=[]
    for name in names:
        n=name.encode('utf8')
        assert len(n)<256
        entry_rows.append(lspk.ENTRY.pack(n+b'\0'*(256-len(n)),lspk.HEADER.size,0,entry_part,compression,len(payload),0 if not compression else 123))
    raw=b''.join(entry_rows);packed=literal(raw);index=struct.pack('<II',len(names),len(packed))+packed
    header=lspk.HEADER.pack(b'LSPK',18,lspk.HEADER.size+len(payload),len(index),4 if solid else 0,0,b'\0'*16,parts)
    path.write_bytes(header+payload+index)
    return raw,len(header),len(payload)


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'Game.pak'
    def tearDown(self):self.tmp.cleanup()
    def test_layout_and_categories_without_payload_reads(self):
        names=['Public/Shared/Stats/Generated/Data/Spell_Test.txt','Mods/Gustav/Story/Generated/story.div.osi','Mods/Gustav/Story/Dialogs/Test.lsj','Localization/English.loca','Textures/Test.dds']
        # Story-containing dialogue paths are classified as dialogue before generic story.
        raw,start,length=fixture(self.path,names)
        real=lspk.read_at;reads=[]
        def observe(stream,offset,size,total):
            reads.append((offset,size));return real(stream,offset,size,total)
        with patch.object(lspk,'read_at',side_effect=observe):r=lspk.inspect(self.path)
        self.assertEqual(r['entries'],5);self.assertEqual(r['index_sha256'],hashlib.sha256(raw).hexdigest())
        for offset,size in reads:self.assertFalse(offset<start+length and offset+size>start)
        self.assertFalse(r['payload_read']);self.assertNotIn(names[0],json.dumps(r))
        self.assertEqual(r['categories']['rules_candidate']['entries'],1)
        self.assertEqual(r['categories']['dialogue_candidate']['entries'],1)
        self.assertEqual(r['repeated_payload_regions'],4)
    def test_independent_byte_offsets_and_high_offset_bounds(self):
        # Build from explicit wire offsets instead of the reader's struct definitions.
        payload=b'fixture'
        name=b'Public/Stats/Data/Rule.txt'
        record=bytearray(272)
        record[:len(name)]=name
        record[256:260]=(40).to_bytes(4,'little')
        record[264:268]=len(payload).to_bytes(4,'little')
        packed=literal(record)
        index=len(payload)+40
        header=b'LSPK'+(18).to_bytes(4,'little')+index.to_bytes(8,'little')+(len(packed)+8).to_bytes(4,'little')+bytes([0,7])+bytes(16)+(1).to_bytes(2,'little')
        self.assertEqual(len(header),40)
        self.path.write_bytes(header+payload+(1).to_bytes(4,'little')+len(packed).to_bytes(4,'little')+packed)
        result=lspk.inspect(self.path)
        self.assertEqual(result['priority_hint'],7)
        self.assertEqual(result['categories']['rules_candidate']['logical_bytes'],7)
        record[260:262]=(1).to_bytes(2,'little')
        packed=literal(record)
        self.path.write_bytes(header+payload+(1).to_bytes(4,'little')+len(packed).to_bytes(4,'little')+packed)
        self.assertEqual(lspk.safe_inspect(self.path)['reason'],'entry_payload_out_of_bounds')
    def test_methods_and_logical_sizes(self):
        for method in range(4):
            fixture(self.path,compression=method)
            r=lspk.inspect(self.path)
            self.assertEqual(r['compression_methods'][lspk.METHODS[method]],1)
            self.assertEqual(r['categories']['rules_candidate']['logical_bytes'],123 if method else len(b'ORIGINAL-FIXTURE-PAYLOAD-DO-NOT-READ'))
    def test_overlap_match_and_literals(self):
        # 1 literal + 19 matched 'a' + final five literals.
        compressed=b'\x1f' + b'a' + b'\x01\x00\x00' + b'\x50' + b'12345'
        self.assertEqual(lspk.lz4_block(compressed,25),b'a'*20+b'12345')
        for n in [0,1,14,15,16,270,4096]:
            raw=bytes(i%251 for i in range(n));self.assertEqual(lspk.lz4_block(literal(raw),n),raw)
    def test_malformed_lz4_and_resource_limits(self):
        for compressed,expected in [(b'\x00\x00\x00',4),(b'\xf0',1),(b'\x10',1),(b'\x10a\x02\x00',5),(b'\x10a',2)]:
            with self.assertRaises(lspk.IndexFailure):lspk.lz4_block(compressed,expected)
        with self.assertRaises(lspk.IndexFailure):lspk.lz4_block(b'',lspk.MAX_DECODED_BYTES+1)
        with self.assertRaises(lspk.IndexFailure):lspk.lz4_block(b'\x00',0,deadline=time.monotonic()-1)
    def test_bad_bounds_unsupported_and_solid(self):
        fixture(self.path,solid=True);self.assertEqual(lspk.safe_inspect(self.path)['reason'],'solid_archive_not_supported')
        fixture(self.path);data=bytearray(self.path.read_bytes());struct.pack_into('<Q',data,8,1<<48);self.path.write_bytes(data)
        self.assertEqual(lspk.safe_inspect(self.path)['status'],'unresolved')
        self.path.write_bytes(b'LSPK'+b'\x12\x00\x00\x00');self.assertEqual(lspk.safe_inspect(self.path)['status'],'unresolved')
    def test_unsafe_names_never_returned(self):
        for name in ['../secret.txt','/absolute.txt','C:/secret.txt','double//path','abc\nprivate.txt']:
            fixture(self.path,[name]);r=lspk.safe_inspect(self.path);self.assertEqual(r['reason'],'unsafe_entry_name');self.assertNotIn(name,json.dumps(r))
    def test_parts_and_missing_parts(self):
        fixture(self.path,parts=2,entry_part=1);self.assertEqual(lspk.safe_inspect(self.path)['reason'],'missing_or_unreadable_archive_part')
        part=self.root/'Game_1.pak';part.write_bytes(b'x'*100)
        self.assertEqual(lspk.inspect(self.path)['parts'],2)
        part.unlink();part.symlink_to(self.path)
        self.assertEqual(lspk.safe_inspect(self.path)['status'],'unresolved')
    def test_budget_and_duplicates(self):
        fixture(self.path,['Public/Test.lsf','Public/Test.lsf'])
        self.assertEqual(lspk.inspect(self.path)['duplicate_path_records'],1)
        self.assertEqual(lspk.safe_inspect(self.path,[0])['reason'],'session_read_limit')
    def test_untrusted_count_deadline_and_archive_mutation(self):
        fixture(self.path)
        data=bytearray(self.path.read_bytes())
        index=int.from_bytes(data[8:16],'little')
        data[index:index+4]=(lspk.MAX_FILES+1).to_bytes(4,'little')
        self.path.write_bytes(data)
        self.assertEqual(lspk.safe_inspect(self.path)['reason'],'index_resource_limit')
        fixture(self.path)
        self.assertEqual(lspk.safe_inspect(self.path,[100000,time.monotonic()-1])['reason'],'index_time_limit')
        real=lspk.os.fstat
        count=[0]
        from types import SimpleNamespace
        def changed(fd):
            info=real(fd);count[0]+=1
            return SimpleNamespace(st_mode=info.st_mode,st_size=info.st_size,st_mtime_ns=info.st_mtime_ns+(1 if count[0]>=3 else 0))
        with patch.object(lspk.os,'fstat',side_effect=changed):
            self.assertEqual(lspk.safe_inspect(self.path)['reason'],'archive_changed_during_scan')
    def test_random_input_never_allocates_from_untrusted_count(self):
        rng=random.Random(1086940)
        for _ in range(500):
            data=bytes(rng.randrange(256) for _ in range(rng.randrange(80)))
            try:
                out=lspk.lz4_block(data,1024)
                self.assertEqual(len(out),1024)
            except lspk.IndexFailure:pass
    def test_reference_lz4_codec_if_available(self):
        try:
            import lz4.block
        except ImportError:
            self.skipTest('independent python-lz4 codec not installed (test-only dependency)')
        rng=random.Random(18)
        for size in [0,1,15,272,4096,65536,200000]:
            for raw in [b'a'*size,bytes(rng.randrange(256) for _ in range(size)),(b'abcde'*(size//5+1))[:size]]:
                compressed=lz4.block.compress(raw,store_size=False)
                self.assertEqual(lspk.lz4_block(compressed,len(raw)),raw)

if __name__=='__main__':unittest.main()
