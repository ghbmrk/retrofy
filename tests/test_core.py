import ctypes
import json
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from collections import deque
from retrofy.core import recover, initial, step, solve, won, Rejected, assess

ROOT=Path(__file__).resolve().parents[1]

class Recovery(unittest.TestCase):
    def test_rejections(self):
        for data in [b'MZ\0exe', b'\xff', b'', b'###\n#@#\n###',
                     b'####\n#@$.\n####', b'####\n#@ #\n##',
                     b'####\n#@*#\n####\n\n####']:
            with self.subTest(data=data), self.assertRaises(Rejected): recover(data)
    def test_search_distinguishes_unknown_and_failure(self):
        ir=recover((ROOT/'fixtures/push.xsb').read_bytes())
        self.assertEqual(solve(ir,1)['status'],'unknown')
        proof=solve(ir); self.assertEqual(proof['status'],'solved')
        s=initial(ir)
        for a in proof['actions']: s=step(ir,s,a)
        self.assertTrue(won(ir,s))
        ir=recover((ROOT/'fixtures/deadlock.xsb').read_bytes())
        self.assertEqual(assess(ir)['decision'],'reject')
    def test_maximum_board(self):
        rows=['#'*20]+['#'+' '*18+'#']*14+['#'*20]
        rows[1]='#@$.'+' '*15+'#'
        ir=recover(('\n'.join(rows)).encode())
        self.assertEqual(ir['width']*ir['height'],320)

class Differential(unittest.TestCase):
    transitions=0
    reachable_counts={}
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        lib=Path(cls.tmp.name)/'kernel.so'
        subprocess.run(['cc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',
                        str(ROOT/'retrofy/native/kernel.c'),'-o',str(lib)],check=True)
        cls.c=ctypes.CDLL(str(lib))
        cls.world=(ctypes.c_uint8*320).in_dll(cls.c,'world')
        cls.player=ctypes.c_uint16.in_dll(cls.c,'player')
        cls.width=ctypes.c_uint16.in_dll(cls.c,'board_w')
        cls.height=ctypes.c_uint16.in_dll(cls.c,'board_h')
        cls.c.move_player.argtypes=[ctypes.c_int8,ctypes.c_int8]
        cls.c.is_won.restype=ctypes.c_uint8
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def compare(self,ir,s,a):
        type(self).transitions+=1
        self.width.value=ir['width']; self.height.value=ir['height']
        for i in range(320): self.world[i]=0
        for k,bit in [('walls',1),('goals',2)]:
            for i in ir[k]: self.world[i]|=bit
        for i in s[1]: self.world[i]|=4
        self.player.value=s[0]
        ctypes.c_uint8.in_dll(self.c,'remaining').value=len(set(s[1])-set(ir['goals']))
        dx,dy={'U':(0,-1),'D':(0,1),'L':(-1,0),'R':(1,0)}[a]
        self.c.move_player(dx,dy)
        expected=step(ir,s,a)
        actual=(self.player.value,tuple(i for i in range(ir['width']*ir['height']) if self.world[i]&4))
        self.assertEqual(actual,expected)
        self.assertEqual(bool(self.c.is_won()),won(ir,expected))
        self.assertEqual(len(actual[1]),len(s[1]))
        self.assertFalse(set(actual[1])&set(ir['walls']))
        return expected
    def test_exhaustive_reachable_states(self):
        for f in ('push.xsb','interactions.xsb','deadlock.xsb'):
            ir=recover((ROOT/'fixtures'/f).read_bytes())
            q=deque([initial(ir)]); seen=set(q)
            while q:
                s=q.popleft()
                for a in 'UDLR':
                    n=self.compare(ir,s,a)
                    if n not in seen: seen.add(n); q.append(n)
            self.assertGreater(len(seen),1)
            type(self).reachable_counts[f]=len(seen)
    def test_randomized_and_mirrored(self):
        rng=random.Random(420)
        for case in range(100):
            w,h=rng.randint(5,20),rng.randint(5,16)
            walls={y*w+x for y in range(h) for x in range(w) if x in (0,w-1) or y in (0,h-1)}
            walls |= {y*w+x for y in range(1,h-1) for x in range(1,w-1) if rng.random()<0.18}
            free=[i for i in range(w*h) if i not in walls]
            rng.shuffle(free); p=free.pop(); boxes=free[:min(10,len(free)//3)]; goals=free[-len(boxes):]
            ir=dict(width=w,height=h,walls=sorted(walls),goals=goals,boxes=boxes,player=p)
            mirror=lambda i:(i//w)*w+w-1-i%w
            mi=dict(width=w,height=h,walls=sorted(map(mirror,walls)),goals=list(map(mirror,goals)),boxes=list(map(mirror,boxes)),player=mirror(p))
            s=initial(ir); ms=initial(mi)
            for _ in range(100):
                a=rng.choice('UDLR'); s=self.compare(ir,s,a)
                ms=step(mi,ms,{'L':'R','R':'L'}.get(a,a))
                self.assertEqual(ms,(mirror(s[0]),tuple(sorted(map(mirror,s[1])))))

if __name__=='__main__': unittest.main()

class Triage(unittest.TestCase):
    def test_control_capacity_is_not_acceptance(self):
        from retrofy.triage import controls
        base=dict(independent_directional_axes=1,simultaneous_non_directional_actions=2,
                  pointer_precision_required=False,text_entry_required=False,external_service_required=False)
        self.assertEqual(controls(base)['decision'],'unresolved')
        for k,v in [('independent_directional_axes',2),('simultaneous_non_directional_actions',3),('text_entry_required',True)]:
            self.assertEqual(controls(dict(base,**{k:v}))['decision'],'reject')
        self.assertEqual(controls({})['decision'],'unresolved')
