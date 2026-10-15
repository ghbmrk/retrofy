import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from .triage import identify, controls
from .core import read_local, recover, assess, digest, canonical, Rejected

ROOT = Path(__file__).resolve().parent

def plan(data):
    ir=recover(data)
    report=assess(ir)
    return dict(schema=1, input_sha256=digest(data), ir=ir, report=report)

def main():
    p=argparse.ArgumentParser(description='Local intake; never runs input games or uploads files')
    sub=p.add_subparsers(dest='cmd', required=True)
    a=sub.add_parser('steam-link'); a.add_argument('--out',required=True); a.add_argument('--port',type=int,default=0)
    a=sub.add_parser('identify'); a.add_argument('input')
    a=sub.add_parser('controls'); a.add_argument('input')
    a=sub.add_parser('plan'); a.add_argument('input'); a.add_argument('--out',required=True)
    a=sub.add_parser('build'); a.add_argument('input'); a.add_argument('--plan',required=True)
    a.add_argument('--approve',required=True, help='SHA-256 of reviewed canonical plan')
    a.add_argument('--rights',required=True,help='Local JSON with access_basis, adaptation_basis, redistribution')
    a.add_argument('--out',required=True); a.add_argument('--lcc',default=os.environ.get('GBDK_LCC','lcc'))
    args=p.parse_args()
    try:
        if args.cmd=='steam-link':
            from .steam import serve
            serve(args.out,args.port); return
        if args.cmd=='identify':
            print(json.dumps(identify(args.input),indent=2)); return
        if args.cmd=='controls':
            print(json.dumps(controls(json.loads(read_local(args.input))),indent=2)); return
        data=read_local(args.input); current=plan(data)
        if args.cmd=='plan':
            out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(canonical(current)+b'\n')
            print(json.dumps(dict(plan=str(out),approve=digest(canonical(current)),decision=current['report']['decision'])))
            return
        reviewed=json.loads(read_local(args.plan))
        if reviewed!=current or digest(canonical(reviewed))!=args.approve:
            raise Rejected('Input/plan changed or approval hash mismatch; review a new plan')
        rights=json.loads(read_local(args.rights))
        for key in ('access_basis','adaptation_basis','redistribution'):
            if not isinstance(rights.get(key),str) or not rights[key].strip():
                raise Rejected('Missing rights field: '+key)
        if current['report']['decision']!='eligible-for-declared-demake':
            raise Rejected('Cannot build rejected or unresolved plan')
        compiler=shutil.which(args.lcc)
        if not compiler: raise Rejected('GBDK lcc unavailable; set GBDK_LCC')
        # Prevent accidental replacement and preserve every attempted build.
        out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
        ir=current['ir']; cells=[0]*(ir['width']*ir['height'])
        for key,bit in [('walls',1),('goals',2),('boxes',4)]:
            for i in ir[key]: cells[i]|=bit
        for file in ('kernel.c','kernel.h','main.c'):
            shutil.copyfile(ROOT/'native'/file,out/file)
        (out/'level.h').write_text('#define LEVEL_W %d\n#define LEVEL_H %d\n#define LEVEL_PLAYER %d\nconst uint8_t level[]={%s};\n' %
            (ir['width'],ir['height'],ir['player'],','.join(map(str,cells))))
        command=[compiler,'-msm83:gb','-Wm-yc','-Wm-yt0','-Wm-yo2','-Wm-ya0','-Wm-ynRETROFY','-Wl-m','-Wl-j','-o','game.gbc','main.c','kernel.c']
        result=subprocess.run(command,cwd=out,capture_output=True,text=True)
        (out/'build.log').write_text(result.stdout+result.stderr)
        if result.returncode: raise Rejected('Compiler failed; inspect '+str(out/'build.log'))
        rom=(out/'game.gbc').read_bytes()
        if len(rom)!=32768 or rom[0x147]!=0 or not rom[0x143]&0x80:
            raise Rejected('Unexpected ROM size, mapper or CGB flag')
        checksum=0
        for b in rom[0x134:0x14D]: checksum=(checksum-b-1)&255
        if checksum!=rom[0x14D]: raise Rejected('Invalid header checksum')
        record=dict(plan=current,approval=args.approve,rights=rights,
            command=[Path(compiler).name]+command[1:],compiler_sha256=digest(Path(compiler).read_bytes()),
            source_sha256={name:digest((out/name).read_bytes()) for name in ('main.c','kernel.c','kernel.h','level.h')},
            rom_sha256=digest(rom),rom_bytes=len(rom),header_checksum='passed',
            evidence={'compiled':True,'emulator':False,'physical':False,'original_differential':False})
        (out/'record.json').write_bytes(canonical(record)+b'\n')
        print(json.dumps(dict(rom=str(out/'game.gbc'),sha256=record['rom_sha256'])))
    except (Rejected,OSError,ValueError) as e:
        print('retrofy: '+str(e),file=sys.stderr); sys.exit(2)

if __name__=='__main__': main()
