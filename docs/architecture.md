# Architecture, alternatives and disproof criteria

The defensible abstraction is a **family of explicit behavioral contracts**, not a universal “game IR.” A binary IR describes machine operations and dependencies; it does not identify which decisions or perceptual cues define a game. A semantic contract must bind each recovered rule to observations, uncertainty and acceptance tests. A native backend must preserve that contract or disclose a departure.

Only `sokoban-grid-v1` is implemented. It stores bounded geometry, walls, goals, boxes and player position. Its executable Python specification and independently written C kernel share no generated movement implementation. Both assume exact integer grid coordinates and atomic cardinal moves: test destination, then the next box cell, then update box and player, then recompute/maintain win state. No continuous time or numerical approximation is implied. The C backend lowers this contract to native SM83 machine code through GBDK, not an interpreter of the source platform.

## Pipeline and implementation status

| Stage | Current implementation | Required extension / decision boundary |
|---|---|---|
| Identify | Bounded streaming SHA-256; PE/DOS, ELF, Mach-O, ZIP magic hints; XSB extension hint | Installation manifest with per-file versions; validated executable headers/imports; engine signatures. Magic alone never accepts a game. |
| Isolate/capture | Inputs are never executed; no sandbox is claimed | Disposable offline VM/container chosen by guest ABI, read-only intake, resource quotas, no credentials, explicit instrumentation rights; bind capture to binary hashes. |
| Analyze | Strict ASCII XSB parser, dimensions/content dependencies | Engine parsers, script decoding and static analysis adapters; enumerate dependencies and preserve unknowns. |
| Recover contract | Layout observed; mechanics declared; differences visible in plan | Trace-backed rule inference; retain competing hypotheses and counterexamples; original update-order/numeric evidence. |
| Assess | Structural limits, control prefilter, bounded BFS solvability; reject/unknown/eligible | Profile workloads and simultaneous controls; classify native port/demake/reinterpretation; no scalar confidence standing in for evidence. |
| Implement | Shared native C backend and generated level array | Additional typed semantic families and per-engine recovery adapters; record bespoke code separately. |
| Optimize | BFS over player/box states for solvability; delta undo and incremental victory/render updates | Representation/scheduling/layout search under invariants; no automatic shrinking, entity reduction, physics changes or turn conversion. |
| Verify | Host C/Python differential; reflection property; exact-ROM PyBoy state/control checks; ROM validation and repeat hashes | Original-runtime traces; CPU cycles and worst-case scanline/transfer profiles; physical Chromatic and independent usability evaluation. |

## Recovery methods by input class

- Engine-managed assets/scripts: first validate container/version, then parse structure without launching scripts. Resource graphs and script bytecode preserve more meaning than disassembling an engine wholesale. Do not assume all games using one engine share gameplay semantics. Unsupported/encrypted data stays opaque.
- Native PE/ELF/Mach-O: [Ghidra](https://github.com/NationalSecurityAgency/ghidra) and debugger traces can locate input polling, update loops, state writes, collision and numeric code. Decompilation is a hypothesis, not source truth. Engine/API boundaries, floating point, threading, undefined behavior and anti-tamper are major barriers. Current tooling only routes these inputs; it does not run Ghidra or recover them.
- Script runtimes: preserve VM version, value semantics, event ordering and library effects. Recover scripts where permitted; test interpreter semantics before lowering. Do not treat scripts as arbitrary trusted build code.
- Controlled black-box execution: reset reproducibly; perturb one action/time/state variable; test boundary collisions, simultaneous inputs, long runs and pathological entity counts. Record seeds, clocks, executable hashes and capture instrumentation. Observationally identical traces do not prove unobserved equivalence.
- Available source/docs: useful oracles and labels; neither a prerequisite nor automatic permission to reuse assets. Compare the shipped binary against source assumptions.

State-machine, fixed-point continuous simulation and rule-rewriting families are proposed next. They must specify numeric widths/rounding/overflow, update order, scheduler/timing, collision rules, random sources, content dependencies and input intent. Rendering, audio and platform services belong in separate contracts, but perceptual cues required for decisions remain invariants. Any abstraction that hides a large hand-written game beneath a small manifest fails the reuse claim.

## Determinism, models and judgment

Use deterministic code for hashing, parsing, lowering, building and replay. Use bounded search for proofs or counterexamples and constrained representation choices. A learned model may propose hypotheses, identify likely subsystems or suggest assets; it may not certify fidelity, rights, feasibility or measurements. Humans must decide experience invariants, material departures, rights/access ambiguities and observed usability. Plan review is tied to the exact canonical plan and input hash; no model approval token exists.

A native port preserves recovered behavior under an explicit equivalence relation. A demake uses a different implementation while preserving declared mechanics and disclosing departures. A creative reinterpretation changes essential rules/decisions/content and requires a separately approved contract. The current adapter always says **demake**; it cannot promote itself to native port. The implementation mechanism alone does not determine classification.

## First experiments likely to falsify the architecture

1. **Closed-source dynamic rules:** capture a legally supplied rule-rewriting puzzle's update order with conflicting rules and simultaneous pushes. Predeclare a set of distinguishing traces; reject the inferred contract if any held-out trace differs. This tests whether grid geometry alone is inadequate (expected).
2. **Continuous timing:** recover one gravity-flip platformer's subpixel integration, collision and frame schedule. Compare frame-aligned state and death outcomes at corner contacts and maximum-speed transitions. A required timing change becomes a reviewed departure, not optimization.
3. **Control impossibility:** independent movement and aiming plus fire may exceed one D-pad and A/B. Require user playtest evidence for any proposed change. Reject direct mapping rather than inserting frequent chords or modal aiming.
4. **Representation transfer:** freeze an adapter/backend before an unseen game from a different architecture. Count all added code, hand-authored rules and intervention. If the new “IR” is chiefly per-game C, reject the reuse hypothesis.
5. **Worst-case native budget:** maximum simultaneous rule interactions/entities and asset changes. Measure cycles, interrupt blocking, stack high-water, VRAM/OAM access and transfer bursts on exact ROM. Reject target settings if invariants cannot fit; do not quietly reduce entity count.
6. **Independent perceptual test:** blinded evaluators list decisions, cues and challenge in original and adaptation. Missing critical cues or materially different optimal strategies fails fidelity even if traces pass.

Completed disproof-oriented experiments: exhaustive unreachable-goal fixture rejection; explicit solver exhaustion; 320-cell/32-box ROM; native undo/restart/blocked moves and simultaneous-direction rejection; geometry reflection. The maximum-board update exposed full-state copy costs: measured solution update latency fell from 11 PyBoy frames to 2 after delta undo/incremental victory. This is a backend experiment, not broad game adaptation.
