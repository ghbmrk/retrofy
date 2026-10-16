# Native next-scene-token experiment

This is an original synthetic prototype, not a BG3 conversion or an LLM. A tiny trained, action-state-conditioned token predictor runs on native SM83 code inside a valid 32 KiB GBC ROM. It autoregresses within an eight-token scene; it does not learn temporal game-state transitions. Those transitions, the renderer and the exact validator are authored code.

**Result: native execution and persistent-state protection work in the tested domain; learned compression superiority is rejected for this fixture.** Direct procedural code is smaller, faster and requires no model repairs.

## Measured comparison

All variants share the same authored mechanics, visuals, controls and reference contract.

| Variant | Physical ROM | Linked ROM extent | Inference + validator ticks (1024 T-cycles) | Input-to-update frames |
|---|---:|---:|---:|---:|
| model | 32,768 B | 6883 B | 61–155 | 1–10 |
| compiled-model | 32,768 B | 8411 B | 19–20 | 1–8 |
| procedural | 32,768 B | 5866 B | 4–4 | 1–7 |

The timer samples are hardware-register measurements inside the emulated CPU, at coarse 1024-T-cycle resolution, including interrupt overhead. They exclude rendering/upload; no inference overflow occurred. The extrema span different contexts and are not paired speedup ratios. Movement reuses a cached scene; its update can take one emulator frame. Full regeneration takes longer. These are not physical-device measurements.

All physical ROMs occupy the minimum 32 KiB; linked extent reports the final occupied ROM address range including header gaps, not a smaller cartridge capacity. Each variant has 500 bytes of linker-allocated static data/HRAM plus separately reserved shadow OAM and unmeasured stack. Sixteen custom background tiles plus console font are used; font VRAM usage was not separately measured. No sprite OAM or audio is used. Full regeneration blanks the LCD temporarily; human usability and display comfort are untested.

## Model and exactness

The model is a masked multiclass integer perceptron: 20 tokens, 32 binary/context features, 640 int8 weight bytes, weights in [-10, 10]. Training uses rooms 0–23 and teacher-forced previous tokens; evaluation free-runs on rooms 24–31. The context includes room traits, local persistent flags and a key bit. This is not a transformer, an LLM, a learned renderer or recovered BG3 semantics.

- 768 training sequences: zero raw mismatches.
- 256 held-out room/state sequences: **52 raw mismatches** (79.6875% exact sequences). These room IDs share the same synthetic mechanic family; this is not cross-game transfer.
- All 2048 possible declared contexts: **104 raw sequence mismatches**. The native validator repairs factual/presentation-contract violations. Its complete canonical logic duplicates the teacher and is included in native size/time. It does not demonstrate that validation is cheaper than implementation.
- The specialized compiled-model variant lowers the same learned coefficients into native conditional arithmetic. Host and exact-ROM checks compare raw proposals against the same frozen predictor before validation, so repairs cannot conceal a compiler mismatch in tested contexts.
- After validation, all variants agree with the independent Python contract/renderer on the tested domain. No learned compression ratio for BG3 is implied.

## Verification and negative controls

- Each variant: 2048 exhaustive host C contexts, 16,384 validated token comparisons and 737,280 tile-ID comparisons.
- Each exact ROM: 1028 checked scenes, including all 1024 stored-room/flag/key contexts (developer-injected) plus controller-driven persistence, key-gated exits and input-edge checks. Each scene checks raw model proposals, eight validated tokens and 360 tile IDs.
- A real controller-input replay opens a chest, gains a key, leaves, changes an NPC state elsewhere and returns. Both changes survive. Persistence is volatile WRAM only, not a battery save or power-cycle guarantee.
- Simultaneous conflicting directions are ignored and a held direction moves once.
- Same-host repeated builds produce identical ROM SHA-256 values for all three variants. Compiler/version provenance follows docs/toolchains.md; only the lcc driver hash is repeated in results.json.

Both the Python contract and C engine were authored for this experiment. Their agreement does not establish original-game equivalence. Exact-ROM checks observe generated RAM state and genuine emulator images; not all runtime frames were visually reviewed. No physical Chromatic, independent user playtest, audio or broad hardware-stress test is claimed.

## Data baselines and honest accounting

For 32 rooms × 16 local flag states × 2 key states, a naive 360-byte tilemap per context costs 368,640 bytes. There are only 192 distinct tilemaps; deduplication plus 16-bit indexes costs 71168 bytes. Host zlib-9 compresses the concatenation to 3888 bytes, excluding an unimplemented native decoder/index. Eight tokens per context cost 8192 bytes. These are data-only comparisons. The conventional procedural ROM is the decisive implementation baseline and wins here.

The original renderer exposed costly per-cell arithmetic. Replacing inner-loop modulo/index arithmetic and caching unchanged scenes reduced observed input-to-update ranges from 18–21 frames in the first full test to the final ranges above. Earlier intermediate builds are not the published ROMs. The initial monolithic compiled predictor also caused an impractically slow SDCC compilation; splitting it by token phase resolved that build problem. All later compiler processes have a 120-second owned process-group budget.

## Reproduce

Use the installed GBDK lcc and Python with PyBoy 2.7.0/Pillow. POSIX hosts only for the current build harness. Choose unused output directories:

```sh
python3 experiments/scene_tokens/experiment.py --out build/my-scenes --lcc /path/to/gbdk/bin/lcc
python3 experiments/scene_tokens/check.py build/my-scenes build/my-scene-checks
```

Training uses Python standard library only; no model API or training download. The second command additionally uses a host C compiler and PyBoy. Inputs are original authored data only. The result scripts refuse to replace existing outputs.

## Next falsifiable step

Test a richer authored visual corpus where scene appearance is expensive but mechanical state remains explicit. Compare a learned motif/token codec against a hand-authored grammar, deduplicated templates and native conventional compression, including all decoder and index costs. Freeze training/test scenes before fitting. No per-held-out-scene repair table or manual patch is allowed.

Next-stage gates: zero mechanically misleading cues, exact persistent-state/revisit tests, faithful held-out scene constraints, at most four emulator frames for a full regeneration and two for ordinary movement, and a measured total native-size win over the strongest conventional baseline before claiming a compression advantage. A small toy that fails these gates remains useful failure evidence. No new Steam Machine action is required for this work.
