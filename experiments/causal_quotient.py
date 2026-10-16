"""Exact future-observation preserving state quotient on original synthetic models.
This is finite-state bisimulation/partition refinement, not a new algorithm or BG3 recovery.
"""
import hashlib
import json
from pathlib import Path

STATES=4096
ACTIONS=4


def transition(state, action, hidden_cause=False):
    core, decoration=state & 255, state >> 8
    hp=core & 3
    wet=bool(core & 8);oil=bool(core & 16)
    if action==0 and hp:
        hp=max(0,hp-(2 if oil and not wet else 1))
    elif action==1:
        core ^= 8
    elif action==2:
        if core & 64:core ^= 128
    elif action==3:
        core ^= 32
    # In the counterexample variant, a latent timer can change a future outcome.
    if hidden_cause and decoration==0 and action==0:
        hp=0
    core=(core & ~3)|hp
    decoration=(decoration+1)&15
    return core|(decoration<<8)


def quotient(hidden_cause):
    # All base facts are observed; decoration is not. Observability is an explicit contract.
    observation=[s & 255 for s in range(STATES)]
    transitions=[[transition(s,a,hidden_cause) for a in range(ACTIONS)] for s in range(STATES)]
    classes=observation[:]
    rounds=0
    while True:
        signatures={};new=[]
        for s in range(STATES):
            key=(observation[s],*(classes[t] for t in transitions[s]))
            if key not in signatures:signatures[key]=len(signatures)
            new.append(signatures[key])
        rounds+=1
        if new==classes:break
        classes=new
    reps={}
    for s,c in enumerate(classes):reps.setdefault(c,s)
    # Every merged state must agree on its observed facts and ALL successor classes.
    checked=0
    for s,c in enumerate(classes):
        representative=reps[c]
        assert observation[s]==observation[representative]
        for a in range(ACTIONS):
            assert classes[transitions[s][a]]==classes[transitions[representative][a]]
            checked+=1
    encoded=bytearray()
    for c in range(len(reps)):
        s=reps[c];encoded.append(observation[s])
        for t in transitions[s]:encoded.extend(classes[t].to_bytes(2,'little'))
    # Two bytes per full-state transition, one observed byte per state in both baselines.
    return dict(variant='latent_gameplay_timer' if hidden_cause else 'cosmetic_only_timer',
                source_states=STATES,quotient_states=len(reps),refinement_rounds=rounds,
                universal_transition_checks=checked,source_table_bytes=STATES*9,
                quotient_table_bytes=len(encoded),quotient_sha256=hashlib.sha256(encoded).hexdigest(),
                current_observation_only_partition_is_sound=not hidden_cause,
                runtime_code_ram_cycles_and_state_mapping='unmeasured; excluded from table-byte counts')


def main():
    result=dict(schema=1,scope='finite synthetic transition systems, not extracted BG3 behavior',
                claim='Observation and successor-class agreement establish all-length trace agreement for this complete finite model and action alphabet.',
                limits=['The observation contract must include essential cues and decisions.',
                        'Missing original state/actions invalidate transfer of this proof.',
                        'No source-state-to-quotient mapping is included in ROM-byte counts.',
                        'A direct native implementation may be smaller than either table.',
                        'No original game, native ROM or hardware performance is evaluated.'],
                results=[quotient(False),quotient(True)])
    path=Path(__file__).resolve().parents[1]/'evidence/causal-quotient.json'
    path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
