"""Independent host-reference and exact-ROM evidence for original scene-token demo."""
import ctypes
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from experiment import TRAITS,teacher,tilemap,train,sequence,predict


def host(build):
    result={}
    weights,_=train()
    for variant,mode in [('model',1),('compiled-model',2),('procedural',0)]:
        target=build/variant;library=target/'engine-host.dylib'
        subprocess.run(['cc','-std=c99','-shared','-fPIC','-O2','-DUSE_MODEL='+str(mode),str(target/'engine.c'),'-o',str(library)],check=True,capture_output=True)
        dll=ctypes.CDLL(str(library));dll.generate.argtypes=[ctypes.c_uint8]*3;dll.render.argtypes=[ctypes.c_uint8]*3
        tokens=(ctypes.c_uint8*8).in_dll(dll,'tokens');pixels=(ctypes.c_uint8*360).in_dll(dll,'screen_map')
        raw=(ctypes.c_uint8*8).in_dll(dll,'proposals')
        repairs=ctypes.c_uint8.in_dll(dll,'repairs');total_repairs=0;scenes=0;cases_repaired=0
        for t in range(64):
            for flags in range(16):
                for key in range(2):
                    expected=teacher(t,flags,key)
                    dll.generate(t,flags,key);assert list(tokens)==expected
                    previous=255
                    for phase,target_token in enumerate(expected):
                        expected_raw=predict(weights,phase,t,flags,key,previous) if mode else target_token
                        assert raw[phase]==expected_raw,(variant,t,flags,key,phase)
                        previous=target_token
                    total_repairs+=repairs.value;cases_repaired+=bool(repairs.value)
                    dll.render(t,flags,key);assert list(pixels)==tilemap(t,flags,key,expected)
                    scenes+=1
        result[variant]=dict(contexts=scenes,token_checks=scenes*8,tile_checks=scenes*360,
                             repaired_proposals=total_repairs,repaired_sequences=cases_repaired,mismatches_after_validation=0)
    return result


def sections(path):
    wanted={}
    for line in path.read_text().splitlines():
        m=re.match(r'^(_\w+)\s+([0-9A-F]{8})\s+([0-9A-F]{8})\s+=',line)
        if m:wanted[m[1]]=dict(address=int(m[2],16),bytes=int(m[3],16))
    rom_areas=[v for k,v in wanted.items() if k.startswith(('_CODE','_HOME','_HEADER','_GS','_INITIALIZER','_LIT','_FONT'))]
    rom=sum(v['bytes'] for v in rom_areas)
    span=max(v['address']+v['bytes'] for v in rom_areas)
    ram=sum(v['bytes'] for k,v in wanted.items() if k in ('_DATA','_INITIALIZED','_BSS','_HRAM'))
    return dict(areas=wanted,linked_rom_section_bytes=rom,linked_rom_extent_bytes=span,static_data_and_hram_bytes=ram,
                limits='Section sum is not physical ROM size. Stack high-water and SDCC reserved shadow OAM are separate.')


def emulated(build,variant,out):
    from pyboy import PyBoy
    out.mkdir(parents=True,exist_ok=False)
    folder=build/variant;rom=folder/'scene.gbc'
    symbols={}
    for line in (folder/'scene.noi').read_text().splitlines():
        fields=line.split()
        if len(fields)==3 and fields[0]=='DEF':symbols[fields[1]]=int(fields[2],16)
    p=PyBoy(str(rom),window='null',sound_emulated=False,cgb=True)
    p.set_emulation_speed(0)
    weights,_=train()
    frames=0;latencies=[];ticks=[];overflows=0;checks=0;interactive=[];stage_times={name:[] for name in ["render","upload"]};stage_overflows={name:0 for name in stage_times}
    def tick(n=1):
        nonlocal frames
        p.tick(n,True);frames+=n
    def get(name):return p.memory[symbols['_'+name]]
    def put(name,value):p.memory[symbols['_'+name]]=value
    def flag(room,value=None):
        address=symbols['_flags']+room
        if value is not None:p.memory[address]=value
        return p.memory[address]
    def press(button):
        old=get('generation');p.button_press(button)
        for n in range(1,61):
            tick()
            if get('generation')!=old:break
        else:raise AssertionError('No completed scene in 60 emulator frames')
        p.button_release(button);tick(2);latencies.append(n)
    def check(label):
        nonlocal checks,overflows
        room=get('room');flags=flag(room);key=get('key');t=TRAITS[room]
        expected=teacher(t,flags,key)
        address=symbols['_tokens'];actual=[p.memory[address+i] for i in range(8)]
        assert actual==expected,(label,actual,expected)
        address=symbols['_proposals'];previous=255
        for phase,target_token in enumerate(expected):
            expected_raw=target_token if variant=='procedural' else predict(weights,phase,t,flags,key,previous)
            assert p.memory[address+phase]==expected_raw,(label,phase,'raw proposal mismatch')
            previous=target_token
        address=symbols['_screen_map'];actual=[p.memory[address+i] for i in range(360)]
        assert actual==tilemap(t,flags,key,expected),label
        ticks.append(get('inference_ticks'));overflows+=get('inference_overflow');checks+=1
        for stage in stage_times:
            stage_times[stage].append(get(stage+'_ticks'));stage_overflows[stage]+=get(stage+'_overflow')
    try:
        for _ in range(180):
            tick()
            if get('ready'):break
        assert get('ready')==1
        tick(2);check('boot');p.screen.image.save(out/'boot.png')
        # Real input sequence: open chest, leave, change another room, return.
        for _ in range(2):press('right')
        for _ in range(2):press('up')
        press('a');assert get('key')==1 and flag(0)&1
        for _ in range(2):press('down')
        for _ in range(15):press('right')
        assert get('room')==1,(get('room'),get('px'),get('py'))
        for _ in range(11):press('right')
        press('a');assert flag(1)&2
        for _ in range(12):press('left')
        assert get('room')==0 and flag(0)&1 and flag(1)&2
        check('persistent-return');p.screen.image.save(out/'persistent-return.png')
        interactive.append('Chest/key and NPC state persist across departure and return using controller inputs.')
        # Seeded exact-ROM tests cover every stored room and bit combination.
        max_repairs=0
        for room in range(32):
            for flags in range(16):
                for key in range(2):
                    put('room',room);put('key',key);put('px',2);put('py',8);flag(room,flags)
                    press('b');check('seeded-'+str(room)+'-'+str(flags)+'-'+str(key));max_repairs=max(max_repairs,get('repairs'))
        put('room',2);put('px',18);put('py',8);put('key',0);flag(2,0)
        press('right');assert get('room')==2
        put('key',1);press('right');assert get('room')==3
        check('gate-key');interactive.append('Locked exit refuses movement without key and allows it with key (seeded state).')
        # Adversarial simultaneous direction set and hold behavior.
        put('px',3);put('py',8);before=(get('room'),get('px'),get('py'))
        p.button_press('up');p.button_press('right');tick(12)
        assert (get('room'),get('px'),get('py'))==before
        p.button_release('up');p.button_release('right');tick(2)
        p.button_press('left');tick(30);p.button_release('left');tick(2)
        assert get('px')==2
        check('held-once');interactive.append('Conflicting directions ignored; held direction performs one step.')
        p.screen.image.save(out/'final.png')
        result=dict(variant=variant,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
                    pyboy=importlib.metadata.version('pyboy'),frames=frames,scene_checks=checks,
                    token_checks=checks*8,tilemap_checks=checks*360,
                    injected_scene_contexts=1024,interactive=interactive,
                    input_to_scene_frames=dict(min=min(latencies),max=max(latencies)),
                    inference_timer_ticks_1024_tcycles=dict(min=min(ticks),max=max(ticks),overflows=overflows),
                    max_repairs_in_one_scene=max_repairs,
                    stage_timer_ticks_1024_tcycles={name:dict(min=min(values),max=max(values),overflows=stage_overflows[name]) for name,values in stage_times.items()},
                    linker=sections(folder/'scene.map'),
                    limits=['Injected contexts are developer tests, not organically reached states.',
                            'Cached movement skips generation; timer samples describe the last full generation.',
                            'Timer measures generate+validator with 1024-T-cycle resolution and interrupt overhead; excludes rendering and VRAM upload.',
                            'Overflow invalidates corresponding timer readings. Input latency is not cycle profiling.',
                            'No power-cycle save persistence (volatile RAM only), audio, original-game comparison, human usability or physical Chromatic test.'])
        (out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:p.stop(save=False)

if __name__=='__main__':
    build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=False)
    results=dict(host=host(build),emulator={})
    for variant in ['model','compiled-model','procedural']:
        results['emulator'][variant]=emulated(build,variant,out/variant)
        print(variant,'exact-ROM checks completed',flush=True)
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
