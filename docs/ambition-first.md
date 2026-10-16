# Ambition-first adaptation: work backward from the experience

## Target and decision boundary

Use **Baldur's Gate 3, single-player offline play**, as the flagship stress target, pending a user-supplied exact installation, platform/version fingerprint and rights ledger. This is a research target, not a compatibility claim or purchase recommendation. Its interacting party combat, exploration, dialogue and persistent consequences challenge substantially more of the architecture than another grid puzzle. Official feature reference: https://baldursgate3.game/about . Source availability is not required; recovery starts with the shipped installation, observable behavior and permitted data/script inspection. Available modding documentation is an auxiliary oracle, not proof of shipped behavior.

There is no uniquely ordered “most ambitious game.” Ambition here means the amount and diversity of essential behavior preserved, not installation size. BG3 tests systemic combinatorics and authored content while its turn-based combat gives A/B/D-pad a plausible route. A real-time independent-aim ARPG may fail controls before compression matters. The current Sokoban backend remains a baseline and regression suite; it does not define the destination.

Start with the full essential experience as the specification. Work backward to necessary state, information, content and hardware costs. Small experiments test the full target's hardest assumptions; they must never be relabeled as a completed adaptation. If necessary departures change essential decisions, report rejection or request approval for a reinterpretation. Multiplayer and online services are outside this declared single-player target; rendering, audio, spatial quantization and text presentation are proposed departures requiring explicit review, not already approved reductions.

Candidate invariants to recover and ratify: action availability and resources, outcome probabilities and random sequencing where equivalence is intended, interaction precedence, party capabilities, visibility/reachability/elevation decisions, quest and dialogue dependencies, irreversible consequences, information needed for tactical choices, and persistence. They are hypotheses about the relevant contract until original-runtime evidence and user review establish them. No automatic party reduction, deleted ability classes, smaller encounters, flattened elevation, invented dialogue or changed combat rules is an optimization.

## What Handwired actually contributes

Sources inspected: https://github.com/chenglou/handwired/blob/main/README.md , https://github.com/chenglou/handwired/blob/main/docs/execution-model.md and https://github.com/chenglou/handwired/blob/main/docs/behavior-choices.md . Handwired expresses state and computation through a small circuit vocabulary and targets JS/WebGPU. Its documentation distinguishes source declarations from proofs and circuit conformance from agreement with the replaced program. It exploits dead-code removal, sharing, declared numeric grids/ranges, one-hot selection and specialized index/gather operations. These are useful architectural lessons.

This does **not** establish that neural networks compress arbitrary programs or that matrix multiplication suits an SM83. Dense floating-point work, evaluating both branches, large intermediate buffers and unrolling loops can increase every relevant cost. Differentiability is potentially useful for offline representation search, not a reason to run a differentiable engine on the cartridge. “Exact” must name numeric semantics and admissible inputs. Reduced decision diagrams, partial evaluation and superoptimization are established approaches; their combination here is a research program, not a claim of newly invented algorithms.

## Proposed family of representations and searches

| Subsystem | Representation candidates | Exactness boundary / failure |
|---|---|---|
| Interaction rules | Sparse event rules; shared predicate DAGs; decision diagrams; bytecode; specialized native routines | Compare legal actions, updates and ordering; state explosion or slow dispatch rejects a representation, not the original mechanics |
| Scripts and quests | Typed effect/condition bytecode; shared subgraphs; packed IDs and dependency indexes; partial evaluation against immutable installation data | Retain provenance and authored branches; never generate replacement prose or erase rare branches to fit |
| Simulation scheduling | Dependency-directed invalidation, change sets, incremental aggregates and transactional event commits | Prove which changes can affect which outputs; stale visibility, changed update order or missed interactions fail |
| World geometry | Visibility/navigation graphs, hierarchical collision, quantized coordinates, portal representations and separately encoded elevation | Preserve relevant reachability, line of sight, ranges and positional choices; a graph abstraction that changes these needs approval |
| Text and assets | Lossless dictionary/grammar coding with seek checkpoints; tile/palette dictionaries; delta animation; procedurally reconstructed repeated geometry | Count decoder, indexes, scratch buffers, bank switches and latency. Lossy art/voice substitutions need inspectable review |
| Search and synthesis | Host-side symbolic simplification, counterexample-guided synthesis and target-cost search; learned proposals with deterministic validation | Training/trace agreement cannot prove unobserved semantics. No model weights accepted as an exact rules substitute without proof |
| Native execution | Hybrid bytecode plus specialized hot kernels; bank-aware data placement; cold-content decoding on demand | Optimize whole ROM, peak RAM, worst-case cycles and player-visible pauses together; no streaming from a Mac/cloud |

A ROM should encode generative rules and shared structure, not enumerate every possible outcome. Authored information with little redundancy still costs space. Code/data tradeoffs are explicit: replacing a table with code or a learned model moves costs; it does not eliminate them. The compiler should compare native code, bytecode, graph and raw-table candidates and preserve a Pareto frontier under measured constraints. No single universal representation is assumed.

Hard target: stock Chromatic, native GBC execution, compatible cartridge, no remote inference, no gameplay coprocessor. ROM tiers for experiments: 256 KiB, 1 MiB and a declared larger supported cartridge. Do not describe the current prototype's ROM size as a hardware ceiling. Standard MBC5's addressable envelope and the actual cartridge's capacity are different constraints; validate mapper, RAM and flash hardware before claiming compatibility. CPU, RAM, VRAM, transfer and scanline budgets remain independent of ROM compression.

## First disproof experiments, before content-scale implementation

1. **Controls and information:** an original synthetic encounter with four controllable party members, elevation, multiple target types, dialogue choices and inspectable consequences. D-pad navigates, A selects/commits, B cancels/backs out. No chords. Measure action-selection steps, mistakes, inspection access and decision visibility against the original. Context menus are allowed only if observed usability is comfortable; small inputs do not excuse disruptive navigation. Set task/time/error thresholds before playtesting, with users, rather than inventing passing scores afterward.
2. **Rule closure:** extract a bounded interaction slice from a fingerprinted legally supplied installation, identify all rules reachable from those actions and preregister adversarial combinations. Test reflected effects, simultaneous effects, deaths, interrupting events and ordering. Freeze a held-out trace set. Refuse to call a hand-authored synthetic encounter BG3 recovery.
3. **Representation search:** lower the same bounded contract to specialized C, compact VM and decision graph. Exhaustively check finite subdomains and generate counterexamples elsewhere. Compile/run the exact ROM; report total linked bytes including runtime, peak working memory and worst-case cycles. Reject any representation whose compressed data hides an oversized/slow decoder.
4. **Content lower bound:** inventory actual text, branches, unique assets and dependencies locally. Measure lossless compressed bytes, random-access indexes and peak decoding buffers; estimate remaining corpus with explicit uncertainty. If authored content alone exceeds the cartridge budget, full-content feasibility fails. Smaller chapters remain separately labeled scope experiments.
5. **Transfer:** freeze the rule/backend machinery before a different game's permitted script/behavior slice, for example Disco Elysium for dialogue and persistent state. Count every new adapter, special rule and manual intervention. Do not claim cross-engine transfer from another generated tactical fixture.

## Completed initial experiment: exact finite-domain data compaction

Run `python3 experiments/semantic_compaction.py`; deterministic output is in `evidence/semantic-compaction.json`. Original synthetic tactical rules combine health, distance, four actions and six flags in a 14-bit domain. A multi-terminal decision graph shares identical branches and tests 24 variable orders. Its actual packed bytes are decoded and checked against all 16,384 reference cases. This is an offline Python experiment, not a native ROM or Handwired benchmark.

- Structured rules: a 32,768-byte uint16 truth table becomes a 664-byte graph, with zero mismatches and at most 13 node visits.
- High-entropy negative control: the graph expands to 81,914 bytes, so selection retains the 32,768-byte raw table.
- These are representation-data sizes only. The selector, decoder code, bank metadata, native execution time and working RAM are not measured. A short native function may beat both representations. The synthetic rules' repetition was chosen to test sharing, not sampled from BG3; no game-size compression factor follows.

This establishes a bounded exact sharing mechanism and an explicit failure case. It establishes no automatic behavioral recovery, full-state scaling, perceptual fidelity, human-effort reduction, real-game conversion, independent evaluation or physical Chromatic result.

## Radical reconstruction, not installation compression

The installation is not the object to squeeze into a cartridge. The object is a new native program whose observable decisions, rules, authored consequences and essential cues satisfy an explicitly approved contract. A 240 GB installation size says little about the minimal description of that contract; it also supplies no evidence that the contract fits. Geometry, renderer code, animation, audio and authored prose have very different information and execution costs. Replacing presentation or omitting content is a declared adaptation decision, not lossless compression.

Work backward through four quantities:

1. **Necessary information:** unique authored choices/content and the rules needed to produce future outcomes. Do not count the original textures as a lower bound on rule storage, or assume unique prose can be synthesized without storing its information somewhere.
2. **Necessary distinctions between states:** merge states only when the preserved observations and all relevant future action outcomes agree. A hidden quest flag may be invisible for hours yet still be indispensable. Reachability from a single save is not permission to delete other campaign branches.
3. **A compact generative implementation:** factor shared predicates/effects, compile sparse event dependencies and bounded integer state, specialize immutable content, and compare native kernels, bytecode, decision graphs and tables. A neural representation competes on total bytes and execution cost; its weights do not make information free.
4. **Hardware execution:** include decoder/interpreter code, data indexes, state encoding, peak RAM, cartridge banking, worst-case cycle counts and input/readability tests. A tiny rules blob with an infeasible runtime fails. No PC/cloud runtime or gameplay coprocessor qualifies.

The whole-game ambition remains the target. A measured, dependency-complete native slice is the disproof instrument, not a replacement deliverable advertised as BG3. Photorealistic audiovisual equivalence is not a credible stock GBC target; essential decisions and consequences require their own concrete tests. No automatic approval exists for changed probabilities, deleted companions, simplified interactions, flattened elevation or rewritten dialogue.

### Completed causal-state experiment

Run `python3 experiments/causal_quotient.py`. `evidence/causal-quotient.json` records exact partition refinement on two original synthetic 4096-state, four-action systems. This is established finite-state bisimulation, used as a testable mechanism rather than a novelty claim.

- A purely cosmetic timer allows 4096 states to become 256. Transition/observation table data changes from 36,864 to 2,304 bytes.
- When that timer can change a delayed gameplay outcome, the valid quotient grows to 2176 states and 19,584 table bytes. The naive 256-state quotient is rejected. Seventeen refinement rounds propagate the delayed distinction.
- For each model, all 16,384 state/action transitions satisfy observation and successor-class agreement. That establishes agreement for every finite action sequence **in these complete finite models**, not merely sampled traces.
- Observation-contract correctness, a mapping from original runtime state, native code, RAM, cycles, sensory fidelity and full-game scalability are unmeasured. Table counts exclude the source-state mapping and runtime. A direct native routine may be smaller. No BG3 state or rule was recovered.

This gives an explicit way to test a radical abstraction: preserve future influence, not just present appearance. Scaling it to BG3 requires compositional contracts and dependency proofs; enumerating the full global state space is not proposed.

## Archive-index reconnaissance v2

The SteamOS package now independently reads bounded non-solid LSPK v18 directory indexes using the public LSLib layout and a bounded pure-Python LZ4 block decoder. It groups filename-derived candidates into rules, story/scripts, dialogue, localization, structured data and presentation classes. It records physical counts/sizes, compression methods and repeated references to the same payload region. It does not decompress any indexed entry payload or save internal resource names.

These measurements answer which next parser/recovery approach is appropriate. They do not establish code semantics, actual duplicates of independently stored contents, dependency closure, load order, effective campaign content size, compression ratio, legal permissions or compatibility. Patch overlays remain unresolved. Unknown/solid/oversized/malformed indexes produce explicit failure codes. Tool resource limits are not hardware limits.

The parser is tested on synthetic original fixtures, explicit byte-offset fixtures, hostile bounds/names/parts and 500 malformed LZ4 inputs. Its decoder is also compared with python-lz4 4.4.4 on 21 independently compressed streams (0 through 200,000 bytes, repetitive and random). That codec is a development-only oracle and is not bundled. No user-game index has yet been run with v2; the user's successful v1 header scan remains separate evidence.

## Native next-scene-token experiment

The [completed experiment and artifacts](../evaluation/scene-tokens/RESULTS.md) test a tiny autoregressive scene-token predictor against compiled-model and direct procedural implementations on native GBC code. Authoritative state remains outside the predictor; an exact validator protects the declared scene contract. Each variant passes 1,028 exact-ROM scene checks including controller-driven revisits. Learned weights total 640 bytes, but the procedural implementation wins total linked ROM usage and inference time. Raw held-out failures and the duplicated canonical validator are counted explicitly.

This falsifies a learned-compression advantage for this synthetic domain. The next meaningful decision boundary is a dependency-complete, authored-content fixture with withheld combinations, comparing total decoder/model/content bytes and worst-case execution against grammar, dictionary and procedural baselines. A representation must preserve delayed consequences and unique authored information; plausible-looking next screens are insufficient. No further user-machine intake is required to develop that experiment.
