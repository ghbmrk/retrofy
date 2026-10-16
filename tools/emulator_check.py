"""Exact-ROM checks using public PyBoy API; does not execute original inputs.
Usage: python tools/emulator_check.py BUILD_DIRECTORY OUTPUT_DIRECTORY
Requires PyBoy==2.7.0, Pillow. Local artifacts only.
"""
import hashlib
import importlib.metadata
import json
import random
from pathlib import Path
import sys
from pyboy import PyBoy

from retrofy.core import initial, step, won

build=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=False)
record=json.loads((build/'record.json').read_text()); ir=record['plan']['ir']
rom=build/'game.gbc'
assert hashlib.sha256(rom.read_bytes()).hexdigest()==record['rom_sha256']
symbols={}
for line in (build/'game.noi').read_text().splitlines():
    fields=line.split()
    if len(fields)==3 and fields[0]=='DEF': symbols[fields[1]]=int(fields[2],16)
p=PyBoy(str(rom),window='null',sound_emulated=False,cgb=True)
p.set_emulation_speed(0)
frames=0; checks=[]
def tick(n=1):
    global frames
    p.tick(n,True); frames+=n

def byte(name): return p.memory[symbols['_'+name]]
def word(name):
    addr=symbols['_'+name]; return p.memory[addr]+256*p.memory[addr+1]
def state():
    base=symbols['_world']
    return word('player'),tuple(i for i in range(ir['width']*ir['height']) if p.memory[base+i]&4)
def verify(expected,label):
    assert state()==expected,(label,state(),expected)
    assert bool(byte('victory'))==won(ir,expected)
    checks.append(dict(label=label,frame=frames,player=expected[0],boxes=list(expected[1])))
def press(button):
    start=byte('generation'); p.button_press(button)
    for elapsed in range(1,31):
        tick()
        if byte('generation')!=start: break
    else: raise AssertionError('No completed update within 30 frames')
    p.button_release(button); tick(2)
    return elapsed
try:
    for _ in range(180):
        tick()
        if byte('ready'): break
    assert byte('ready')==1
    tick(2)  # LCD must complete a frame before capturing the boot framebuffer.
    expected=initial(ir); verify(expected,'boot')
    p.screen.image.save(out/'boot.png')
    latencies=[]; history=None
    mapping={'U':'up','D':'down','L':'left','R':'right'}
    for index,a in enumerate(record['plan']['report']['solver']['actions']):
        before=expected; expected=step(ir,expected,a)
        if expected!=before: history=before
        latencies.append(press(mapping[a])); verify(expected,'solution-'+str(index))
    assert won(ir,expected)
    p.screen.image.save(out/'solved.png')
    press('b'); expected=history; verify(expected,'undo')
    press('a'); expected=initial(ir); verify(expected,'restart')
    # Holding a direction must cause exactly one move, with no repeats.
    p.button_press('right'); tick(30); expected=step(ir,expected,'R'); verify(expected,'held-right-30')
    p.button_release('right'); tick(2)
    # Multiple directions ignored. Action generation remains unchanged.
    before=state(); g=byte('generation')
    p.button_press('left'); p.button_press('up'); tick(10)
    assert state()==before and byte('generation')==g
    p.button_release('left'); p.button_release('up'); tick(2)
    checks.append(dict(label='two-directions-ignored',frame=frames))
    press('a'); expected=initial(ir); history=None
    rng=random.Random(20261015)
    for index in range(256):
        a=rng.choice('UDLRBA')
        if a=='A':
            press('a'); expected=initial(ir); history=None
        elif a=='B':
            if history is None:
                p.button_press('b'); tick(12); p.button_release('b'); tick(2)
            else:
                press('b'); expected=history; history=None
        else:
            before=expected; expected=step(ir,expected,a)
            if expected!=before: history=before
            press(mapping[a])
        verify(expected,'seeded-'+str(index)+'-'+a)
    p.screen.image.save(out/'after-seeded.png')
    result=dict(rom_sha256=record['rom_sha256'],pyboy=importlib.metadata.version('pyboy'),mode='CGB',
        frames=frames,checks=checks,solution_update_frames=latencies,
        limitations=['frame latency is not CPU-cycle profiling','no original-game differential',
                      'no human usability assessment','no physical hardware','audio disabled'])
    (out/'emulator.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'} | {'checks':len(checks)}))
finally: p.stop(save=False)
