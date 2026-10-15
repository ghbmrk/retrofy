# Benchmark protocol: qualification before conversion

No user game or version was supplied in the development session. Consequently **zero user-owned games and zero closed-source games have been evaluated**. No game was downloaded as a substitute for the user's installation. The following is a pre-registered research shortlist, not a compatibility list or an assertion of access/ownership/permissions. Supply exact local versions and a rights ledger before enrollment.

| Candidate / architecture to confirm from local files | Essential experience / acceptable departures | Likely invalidator; smallest native experiment | Acceptance / rejection before implementation |
|---|---|---|---|
| User's existing Sokoban implementation plus a permitted XSB level; original runtime must be fingerprinted | Spatial pushing decisions and deadlocks. New art acceptable only in declared demake; scoring, undo and repeat timing separately reviewed | Original move/undo semantics and board scale; one board with collision, box-on-goal and deadlock traces | No movement-state mismatches on exhaustive small boards + recorded original traces; reject unknown rules, lost geometry, or unreadable board |
| [Baba Is You](https://www.hempuli.com/Baba/), commercial executable/data; engine/ABI unconfirmed | Physical words alter rules; rule conflict/order matters. Palette/art changes only after readable words demonstrated | Dynamic rule resolution and simultaneous entity effects; native smallest conflicting-rule room | Predeclare distinguishing rule traces and worst-case rule/entity workload; reject any missed essential interaction or unreadable rule text. Do not turn this into ordinary Sokoban |
| [VVVVVV](https://github.com/TerryCavanagh/VVVVVV), native executable; source as optional oracle | Momentum, gravity reversal, precise hazards, room transitions. Reviewed art/audio changes possible | Numerical collision/timing; native maximum-speed corner/flip experiment | Frame-aligned collision/death/transition traces under replay; any timing tolerance must be declared before testing. Review the [custom source license](https://github.com/TerryCavanagh/VVVVVV/blob/master/LICENSE.md); source visibility does not license all assets |
| [OpenTTD](https://www.openttd.org/downloads/openttd-releases/latest), native simulation; negative/control workload candidate | Network construction, economic feedback and large-system information | Pointer/UI bandwidth, scale and pathfinding; small network simulation + A/B navigation usability test | Reject direct adaptation if essential decisions require disruptive navigation or workload cannot fit. A tiny train toy is a creative reinterpretation, not a successful port. [Core/content licensing differs](https://www.openttd.org/content-creators) |

The shortlist spans data-defined discrete puzzles, commercial dynamic rules, native continuous platforming and large simulation. Architecture claims must be confirmed from each submitted version; engine names are not evidence. A second closed-source game from a different engine should be assigned to held-out evaluation only after intake. This selection is pending, not silently filled with another puzzle fixture.

Before implementing any real candidate, record:

1. Hash manifest of executable/libraries/data, platform/ABI, exact version, dependencies, permitted access/changes and public-artifact restrictions.
2. Essential decisions, cues, controls, timing and invariants; category (native port/demake/reinterpretation), departures and approval hash.
3. Representative and pathological input traces, seeds/clocks and state observations; distinguish direct observations, inferred rules, adaptation choices and untested hypotheses.
4. Preregister acceptance tests, tolerances, worst-case workload, performance budget and independent usability procedure. Reject ambiguous success criteria before conversion.
5. Freeze reusable adapter/backend and test corpus; retain failed hypotheses and counterexamples. Capture before/after source diff and labor log.

## Generalization and effort accounting

Split by **game and runtime architecture**, not level. Never train or tune on held-out evaluation traces. Report separately:

- Conversion: enrolled/attempted/compiled/behaviorally accepted/physical-tested counts and all rejection reasons.
- Fidelity: original-state differential outcomes, mechanics properties, essential decision/cue evaluation, and disclosed changes. Synthetic spec conformance is a separate metric.
- Performance: worst-case cycles, static and peak RAM/stack, VRAM, tile transfers by frame/scanline, OAM totals/overlap, ROM/bank footprint; label unmeasured quantities.
- Effort: added game-specific versus shared lines/AST nodes; adapter changes; manually specified rules/content; analyst minutes, review decisions, failed experiments and elapsed machine time. A configuration file encoding an entire game counts as bespoke work.
- Transfer: frozen backend success on unfamiliar games, interventions and incremental cost. Another level using the same engine is not architecture transfer.

Current results cover four synthetic boards (one mechanics family), one exhaustive deadlock rejection, randomized generated geometries and no unfamiliar games. Human effort was not instrumented; no time-saving factor is claimed. Later benchmark results must preserve this baseline rather than retroactively relabel fixtures as commercial conversions.
