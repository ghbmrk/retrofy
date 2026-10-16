"""Train a tiny integer next-scene-token model on original synthetic scenes.
No language model, BG3 input or automatic game adaptation is claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import time
import os
import signal
import zlib

TRAITS=[((r*13)^(r>>1))&63 for r in range(32)]
GROUPS=[(0,4),(4,4),(8,2),(10,2),(12,2),(14,2),(16,2),(18,2)]
FEATURES=32
ROOT=Path(__file__).resolve().parent


def teacher(traits,flags,key):
    theme=traits&3
    return [theme,4+((theme+1)&3),8+bool(traits&4),
            10+bool(flags&8 and not traits&4),12+bool(flags&1),
            14+int(not flags&2),16+bool(traits&16 and not key),18+bool(flags&4)]


def features(traits,flags,key,previous):
    context=traits|(flags<<6)|(key<<10)
    return [0]+[b+1 for b in range(11) if context&(1<<b)]+([12+previous] if previous<20 else [])


def predict(weights,phase,traits,flags,key,previous):
    start,count=GROUPS[phase];active=features(traits,flags,key,previous)
    return max(range(start,start+count),key=lambda token:sum(weights[token][i] for i in active))


def sequence(weights,traits,flags,key):
    output=[];previous=255
    for phase in range(8):
        previous=predict(weights,phase,traits,flags,key,previous);output.append(previous)
    return output


def train():
    weights=[[0]*FEATURES for _ in range(20)]
    examples=[]
    for room in range(24):
        for flags in range(16):
            for key in range(2):
                previous=255
                for phase,target in enumerate(teacher(TRAITS[room],flags,key)):
                    examples.append((phase,TRAITS[room],flags,key,previous,target));previous=target
    rng=random.Random(20261016)
    epochs=[]
    for epoch in range(80):
        rng.shuffle(examples);errors=0
        for phase,traits,flags,key,previous,target in examples:
            chosen=predict(weights,phase,traits,flags,key,previous)
            if chosen!=target:
                errors+=1
                for i in features(traits,flags,key,previous):
                    weights[target][i]+=1;weights[chosen][i]-=1
        epochs.append(errors)
        if not errors:break
    if max(abs(x) for row in weights for x in row)>127:
        raise ValueError('Weights do not fit int8; quantization requires a new experiment')
    return weights,epochs


def tilemap(traits,flags,key,tokens):
    # Independent host renderer describes an original authored demonstration.
    out=[128]*(20*18)
    theme=tokens[0];trim=tokens[1]-4
    for y in range(2,17):
        for x in range(20):
            out[y*20+x]=(143 if trim&1 else 129) if x in (0,19) or y in (2,16) else 128
            if 0<x<19 and 2<y<16 and (x+y+theme)%7==0:out[y*20+x]=140
    for x in range(1,19):out[10*20+x]=130 if tokens[2]==9 else 128
    for x,y in [(0,8),(19,8),(10,2),(10,16)]:out[y*20+x]=128
    out[6*20+5]=133 if tokens[4]==13 else 132
    out[8*20+13]=134 if tokens[5]==15 else 135
    out[10*20+9]=131 if tokens[3]==11 else 141
    out[8*20+18]=136 if tokens[6]==17 else 137
    out[13*20+9]=138 if tokens[7]==19 else 142
    return out


def analyze(weights,epochs):
    counts=dict(training_sequences=0,training_mismatches=0,heldout_room_sequences=0,heldout_room_mismatches=0,
                exhaustive_context_sequences=0,exhaustive_context_mismatches=0)
    for room,traits in enumerate(TRAITS):
        for flags in range(16):
            for key in range(2):
                name='training' if room<24 else 'heldout_room'
                counts[name+'_sequences']+=1
                counts[name+'_mismatches']+=sequence(weights,traits,flags,key)!=teacher(traits,flags,key)
    for traits in range(64):
        for flags in range(16):
            for key in range(2):
                counts['exhaustive_context_sequences']+=1
                counts['exhaustive_context_mismatches']+=sequence(weights,traits,flags,key)!=teacher(traits,flags,key)
    maps=[bytes(tilemap(t,f,k,teacher(t,f,k))) for t in TRAITS for f in range(16) for k in range(2)]
    unique=set(maps)
    return dict(schema=1,scope='original synthetic next-scene-token experiment',
                model='masked multiclass integer perceptron; teacher-forced training, free-running evaluation',
                model_weight_bytes=20*FEATURES,weight_range=[min(min(r) for r in weights),max(max(r) for r in weights)],
                epochs=epochs,counts=counts,scene_tokens=8,rooms=32,mutable_bits_per_room=4,
                raw_tilemap_bytes=32*16*2*360,unique_tilemaps=len(unique),
                deduplicated_tilemap_data_and_uint16_index_bytes=len(unique)*360+len(maps)*2,
                zlib9_tilemap_bytes=len(zlib.compress(b''.join(maps),9)),
                token_table_bytes=32*16*2*8,
                limits=['Not an LLM or learned game mechanics. The teacher and renderer are hand-written.',
                        'Held-out room IDs share the same synthetic mechanics; not cross-game transfer.',
                        'Exact factual-token validation contains duplicate teacher logic and must be charged to total implementation size.',
                        'A procedural implementation is a serious baseline, not just stored screens.',
                        'Data sizes exclude decoder/runtime/banking/padding; native builds supply separate totals.',
                        'zlib is a host-side data baseline only; no native decompressor is implemented.',
                        'Token autoregression is within a scene, not a learned temporal world model.',
                        'No proprietary game input, original-game equivalence or physical hardware test.'])


def compiled_predictor(weights):
    lines=[]
    for phase,(start,count) in enumerate(GROUPS):
        lines+=['static uint8_t predict_'+str(phase)+'(uint16_t context,uint8_t previous){',
                'int16_t score,best=-32767;uint8_t chosen=0;']
        for token in range(start,start+count):
            row=weights[token];lines.append('score='+str(row[0])+';')
            for feature,coefficient in enumerate(row[1:],1):
                if not coefficient:continue
                condition='(context&'+str(1<<(feature-1))+')' if feature<=11 else '(previous=='+str(feature-12)+')'
                lines.append('if'+condition+' score+='+str(coefficient)+';')
            lines.append('if(score>best){best=score;chosen='+str(token)+';}')
        lines+=['return chosen;','}']
    lines+=['static uint8_t compiled_predict(uint8_t phase,uint8_t t,uint8_t f,uint8_t k,uint8_t previous){',
            'uint16_t context=(uint16_t)t|((uint16_t)f<<6)|((uint16_t)k<<10);','switch(phase){']
    for phase in range(8):lines.append('case '+str(phase)+':return predict_'+str(phase)+'(context,previous);')
    lines+=['}', 'return 0;', '}']
    return '\n'.join(lines)


def header(weights):
    return '#ifndef MODEL_DATA_H\n#define MODEL_DATA_H\n#if USE_MODEL==1\nconst int8_t weights[20][32]={\n'+',\n'.join('{'+','.join(map(str,r))+'}' for r in weights)+'\n};\n#elif USE_MODEL==2\n'+compiled_predictor(weights)+'\n#endif\nconst uint8_t traits[32]={'+','.join(map(str,TRAITS))+'};\n#endif\n'


def build(out,lcc):
    out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    weights,epochs=train();report=analyze(weights,epochs)
    (out/'model.h').write_text(header(weights))
    (out/'training.json').write_text(json.dumps(report,indent=2)+'\n')
    for name in ['engine.c','engine.h','main.c']:
        shutil.copyfile(ROOT/name,out/name)
    builds={}
    # Both variants use the same input/state, grammar validator and native renderer.
    for variant,mode in [('model',1),('compiled-model',2),('procedural',0)]:
        target=out/variant;target.mkdir()
        for name in ['engine.c','engine.h','main.c','model.h']:shutil.copyfile(out/name,target/name)
        command=[lcc,'-msm83:gb','-Wm-yc','-Wm-yt0','-Wm-yo2','-Wm-ya0','-Wm-ynSCENETOKENS','-Wl-m','-Wl-j','-DUSE_MODEL='+str(mode),'-o','scene.gbc','main.c','engine.c']
        started=time.perf_counter()
        process=subprocess.Popen(command,cwd=target,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        try:
            stdout,stderr=process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate()
            (target/'build.log').write_text(stdout+stderr+'\nCompiler process-group time limit exceeded.\n')
            raise RuntimeError('Compiler exceeded 120-second budget')
        (target/'build.log').write_text(stdout+stderr)
        if process.returncode:raise RuntimeError('Build failed; inspect '+str(target/'build.log'))
        rom=(target/'scene.gbc').read_bytes()
        assert len(rom)==32768 and rom[0x147]==0 and rom[0x143]&0x80
        check=0
        for b in rom[0x134:0x14d]:check=(check-b-1)&255
        assert check==rom[0x14d]
        builds[variant]=dict(rom_bytes=len(rom),rom_sha256=hashlib.sha256(rom).hexdigest(),
                             command=[Path(lcc).name]+command[1:],compiled=True,emulator=False,build_seconds=round(time.perf_counter()-started,3))
    (out/'builds.json').write_text(json.dumps(builds,indent=2)+'\n')
    print(json.dumps(dict(training=report,builds=builds),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--lcc',required=True);a=p.parse_args();build(a.out,a.lcc)
