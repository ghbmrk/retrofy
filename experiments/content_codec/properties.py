"""Different seeds and single-symbol changes; no native timing claim."""
import json
import random
from experiment import CODECS, CORPORA, corpus, dictionary, encode, decode


def check():
    cases = 0
    for name in CORPORA:
        book = dictionary(corpus(name))
        for seed in range(40):
            rng = random.Random(70000 + seed)
            original = bytes(rng.randrange(5) for _ in range(360))
            changed = bytearray(original)
            pos = rng.randrange(360)
            changed[pos] = (changed[pos] + 1) % 5
            changed = bytes(changed)
            for codec in CODECS:
                before = decode(codec, encode(codec, original, book), book)
                after = decode(codec, encode(codec, changed, book), book)
                assert before == original and after == changed
                assert sum(a != b for a, b in zip(before, after)) == 1
                cases += 1
    assert corpus('shared')[:24] == corpus('novel')[:24]
    assert dictionary(corpus('shared')) == dictionary(corpus('novel'))
    return dict(exact_metamorphic_cases=cases, round_trips=2 * cases,
                seeds=list(range(70000, 70040)), mismatches=0,
                frozen_training_same_across_shared_and_novel=True,
                limits='Host codecs on different random seeds, not commercial-input or native transfer evidence.')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
