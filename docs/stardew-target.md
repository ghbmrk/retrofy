# Flagship research target: Stardew Valley (pending enrollment)

Proposed target: a purchased, unmodded desktop Steam installation, AppID 413150. Exact platform/build/file hashes must be enrolled after local installation; no version has been acquired or analyzed. Purchase: https://store.steampowered.com/app/413150/Stardew_Valley/ . The official store listed USD $14.99 when checked on 2026-10-15; region/checkout determines the actual price. The developer's press page reports over 41 million copies as of December 2024: https://www.stardewvalley.net/press/ . That supports popularity, not conversion feasibility.

This is more ambitious than the initial grid family because economic decisions, world/calendar progression, NPC schedules, dialogue, persistent map changes, inventories, crafting, fishing and combat interact. The intended target is offline single-player. Multiplayer exclusion is an explicit scope decision requiring approval in any concrete adaptation plan; it must not be silently labeled full-game equivalence.

## Preserve or reject

Preserve the enrolled version's world connectivity and meaningful travel time, daily/seasonal causality, crop/economic rules, content-dependent progression, NPC schedules, resource/energy tradeoffs, and defining minigame/combat decisions. Do not replace this with a small farming game, reduce world/entity/content counts as an undisclosed optimization, or make real-time mechanics turn-based.

Control hypothesis only: D-pad movement/menu navigation; A tool/action; B interaction/cancel, with contextual menus for inventory and auxiliary actions. This mapping is **not accepted**: tool switching, inventory access, fishing and combat may require frequent disruptive modes. That is a possible rejection reason even if code fits. Context sensitivity must be inspected and usability measured with original gameplay tasks.

## First invalidating experiments (before full adaptation)

1. Recover exact state/event order across a day boundary with crops, machines, NPC schedule and quest conditions. Replay the same bounded original scenario and compare every observed transition. A manually invented crop model does not pass.
2. Prototype native inventory/tool selection while moving, farming, fishing and fighting. Observe task completion, selection errors and interruptions. Reject a mapping that needs frequent chords or disruptive menus; preregister thresholds with the user after original task capture.
3. Stream original-scale connected map data and maintain representative persistent changes within measured cartridge/WRAM budgets. Measure worst-case room/region transitions. Cropping into a smaller world is not a valid pass.
4. Recover and replay fishing/combat numerical behavior and timing. Verify frame schedule, collision and input response; any material departure needs approval.
5. Identify the actual managed/native runtime and asset container versions from local files before choosing analyzers. A managed-code/engine-aware approach is a hypothesis until verified; no executable lifting, script recovery or decompilation has yet been performed.

The first conversion gate is these experiments, not a promise to ship a full native Stardew Valley ROM. Acquisition/ownership, extraction/modification permission and distribution permission remain distinct. No developer contact or rights request has been sent.
