"""Exact finite-domain representation search. Original synthetic data only; no game recovery."""
import hashlib
import json
import random
import struct
from pathlib import Path

BITS = 14
TAG = 0x8000

def tactical(x):
    hp = x & 7
    alive, wet, oil, burning, visible, quest = [(x >> b) & 1 for b in range(3, 9)]
    action, distance = (x >> 9) & 3, (x >> 11) & 7
    legal = bool(alive and hp and visible)
    cost, changed = 0, 0
    if action == 0:
        legal &= distance <= 1
        if legal:
            hp = max(0, hp - (1 if wet else 2)); cost = 1
    elif action == 1:
        legal &= distance <= 4
        if legal:
            burning = int(not wet); hp = max(0, hp - (3 if oil and not wet else 1)); cost = 2
    elif action == 2:
        legal &= distance <= 1
        if legal:
            hp = max(0, hp - int(distance == 0)); cost = 1
    else:
        legal &= distance <= 2 and not burning
        if legal:
            changed = quest; cost = 1
    return hp | (burning << 3) | (int(legal) << 4) | (cost << 5) | (changed << 7)

def compile_graph(table, order):
    nodes, unique = [], {}
    def build(depth, state):
        if depth == BITS:
            return TAG | table[state]
        bit = order[depth]
        low = build(depth + 1, state)
        high = build(depth + 1, state | (1 << bit))
        if low == high:
            return low
        key = bit, low, high
        if key not in unique:
            if len(nodes) >= TAG:
                raise ValueError('16-bit node index capacity exceeded')
            unique[key] = len(nodes)
            nodes.append(key)
        return unique[key]
    root = build(0, 0)
    return struct.pack('<HH', root, len(nodes)) + b''.join(struct.pack('<BHH', *n) for n in nodes)

def evaluate(blob, state):
    node, count = struct.unpack_from('<HH', blob)
    visits = 0
    while not node & TAG:
        if node >= count:
            raise ValueError('invalid node')
        bit, low, high = struct.unpack_from('<BHH', blob, 4 + 5 * node)
        node = high if state & (1 << bit) else low
        visits += 1
        if visits > BITS:
            raise ValueError('cyclic or invalid graph')
    return node & ~TAG, visits

def measure(name, fn, orders):
    table = [fn(x) for x in range(1 << BITS)]
    assert all(0 <= n < TAG for n in table)
    raw = struct.pack('<' + 'H' * len(table), *table)
    candidates = [(compile_graph(table, order), order) for order in orders]
    blob, order = min(candidates, key=lambda pair: (len(pair[0]), pair[1]))
    worst, mismatches = 0, 0
    for x, expected in enumerate(table):
        actual, visits = evaluate(blob, x)
        mismatches += actual != expected
        worst = max(worst, visits)
    assert mismatches == 0
    return dict(name=name, domain_cases=len(table), orders_searched=len(orders),
                raw_table_bytes=len(raw), graph_bytes=len(blob), graph_nodes=(len(blob)-4)//5,
                graph_to_table_ratio=round(len(blob)/len(raw), 6), worst_node_visits=worst,
                selected='graph' if len(blob) < len(raw) else 'raw_table',
                selected_data_bytes=min(len(blob), len(raw)), mismatches=mismatches,
                order=order, graph_sha256=hashlib.sha256(blob).hexdigest(),
                reference_table_sha256=hashlib.sha256(raw).hexdigest())

def main():
    rng = random.Random(20261015)
    orders = [list(range(BITS)), list(reversed(range(BITS)))]
    for _ in range(22):
        order = list(range(BITS)); rng.shuffle(order); orders.append(order)
    result = dict(schema=1, scope='synthetic finite-domain exact data compaction; not a game conversion',
                  limitations=['Table baseline is not original source or optimized native C.',
                               'Decoder machine-code bytes, banking, native cycles and RAM are unmeasured.',
                               'Exhaustive tests cover only the declared 14-bit domain.',
                               'Decision diagrams and variable-order search are established techniques, not a novelty claim.',
                               'No Handwired execution, trained model or proprietary input is used.'],
                  results=[measure('interacting_tactical_rules', tactical, orders),
                           measure('high_entropy_negative_control', lambda x: int.from_bytes(hashlib.sha256(struct.pack('<H', x)).digest()[:2], 'little') & 0x7fff, orders)])
    path = Path(__file__).resolve().parents[1] / 'evidence/semantic-compaction.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
