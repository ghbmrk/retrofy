"""Bounded content recovery and an executable behavioral specification. No input execution."""
import hashlib
import json
from collections import deque
from pathlib import Path

MAX_INPUT = 65536
PROFILE = 'sokoban-grid-v1'

class Rejected(ValueError):
    pass

def read_local(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise Rejected('Input must be a regular, non-symlink file')
    with p.open('rb') as f:
        data = f.read(MAX_INPUT + 1)
    if len(data) > MAX_INPUT:
        raise Rejected('Input exceeds 64 KiB intake limit')
    return data

def recover(data):
    """One strict XSB board. Rules are declared, never inferred from XSB."""
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError as e:
        raise Rejected('Only ASCII XSB is supported; executable/archive recovery unavailable') from e
    rows = text.splitlines()
    if not rows or any(not r for r in rows):
        raise Rejected('Exactly one board, no blank separators or metadata')
    w, h = max(map(len, rows)), len(rows)
    if not (3 <= w <= 20 and 3 <= h <= 16):
        raise Rejected('Board must fit 20 x 16 without resizing or cropping')
    if any(len(r) != w for r in rows):
        raise Rejected('Ragged board: implicit outside-space semantics are ambiguous')
    if any(c not in '# .@$*+' for r in rows for c in r):
        raise Rejected('Unsupported symbols or metadata')
    if any(rows[y][x] != '#' for y in range(h) for x in range(w)
           if x in (0, w-1) or y in (0, h-1)):
        raise Rejected('Board must have an explicit wall perimeter')
    cells = ''.join(rows)
    players = [i for i,c in enumerate(cells) if c in '@+']
    boxes = [i for i,c in enumerate(cells) if c in '$*']
    goals = [i for i,c in enumerate(cells) if c in '.*+']
    if len(players) != 1 or not boxes or len(boxes) != len(goals):
        raise Rejected('Require one player and equal, nonzero box/goal counts')
    if len(boxes) > 32:
        raise Rejected('Current implementation supports at most 32 boxes')
    return dict(schema=1, profile=PROFILE, width=w, height=h,
                walls=[i for i,c in enumerate(cells) if c=='#'],
                goals=goals, boxes=boxes, player=players[0])

def initial(ir):
    return (ir['player'], tuple(sorted(ir['boxes'])))

def step(ir, state, action):
    p, boxes = state
    if action not in 'UDLR' or len(action) != 1:
        raise Rejected('Actions must be U/D/L/R')
    w,h = ir['width'],ir['height']
    dx,dy = {'U':(0,-1),'D':(0,1),'L':(-1,0),'R':(1,0)}[action]
    x,y = p%w+dx,p//w+dy
    if not(0<=x<w and 0<=y<h): return state
    q=y*w+x
    if q in ir['walls']: return state
    b=set(boxes)
    if q in b:
        x,y=x+dx,y+dy
        if not(0<=x<w and 0<=y<h): return state
        r=y*w+x
        if r in ir['walls'] or r in b: return state
        b.remove(q); b.add(r)
    return q,tuple(sorted(b))

def won(ir,state):
    return set(state[1]) == set(ir['goals'])

def solve(ir, limit=100000):
    start=initial(ir); queue=deque([(start,'')]); seen={start}
    while queue:
        s,trace=queue.popleft()
        if won(ir,s): return dict(status='solved',actions=trace,states=len(seen))
        for a in 'UDLR':
            n=step(ir,s,a)
            if n not in seen:
                if len(seen)>=limit:
                    return dict(status='unknown',reason='state budget exhausted',states=len(seen))
                seen.add(n); queue.append((n,trace+a))
    return dict(status='rejected',reason='exhaustively unsolvable',states=len(seen))

def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()

def assess(ir):
    proof=solve(ir)
    return dict(decision={'solved':'eligible-for-declared-demake','unknown':'unresolved','rejected':'reject'}[proof['status']],
        solver=proof, classification='demake', native_port=False,
        controls={'dpad':'one edge-triggered cardinal move; no repeat', 'A':'restart', 'B':'one-level undo'},
        simultaneous_actions='opposing/multiple directions ignored; no chords required',
        departures=['new tile art; no source audio', 'discrete input timing; no held-key repeat',
                    'single board; no original menus, scoring, narrative, saves or progression',
                    'one-level undo; restart is immediate'],
        evidence={'observed':'board bytes and structure', 'declared':'sokoban-grid-v1 rules',
                  'inferred':[], 'untested':['original executable equivalence','feel','physical Chromatic']},
        limits={'board_cells':320,'boxes':32,'cartridge':'32 KiB ROM-only; no SRAM',
                'sprites':0,'scanline_sprites':0,'tile_bytes':128,
                'cpu_cycles':'unmeasured; emulator/hardware measurement required'})
