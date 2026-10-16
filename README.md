# Retrofy

Local game adaptation research for native Game Boy Color ROMs intended for a stock ModRetro Chromatic. **Research prototype, not an arbitrary-game converter.**

Working today: strict single-board ASCII XSB intake → SHA-256 fingerprint → declared Sokoban grid specification → bounded solvability search → inspectable demake plan → native GBDK C → 32 KiB ROM → exact-ROM PyBoy checks. A/B/D-pad only. No emulated source engine, runtime dependency on a PC, input upload, or input execution.

**No existing commercial game has been converted or verified.** Included boards are original synthetic MIT conformance fixtures. The pipeline recovers their layout; their mechanics are declared, not inferred from an executable. It cannot establish fidelity to a particular Sokoban product. Three boards exercise one mechanics family, not broad generalization.

## Native scene-generation research

The [experimental loop](docs/experimental-loop.md) now includes [exact content-codec results](evaluation/content-codec/RESULTS.md): 18 native ROM variants, frozen unseen-content tests, actual VRAM checks and measured size/latency selection. Shared motifs favor dictionaries; unfamiliar motifs expand and random content favors bit packing. Full updates take 2–4 emulator frames and cached movement takes one, with VBlank DMA replacing LCD blanking. These remain original synthetic experiments, not commercial-game conversions.

A [working next-scene-token experiment](evaluation/scene-tokens/RESULTS.md) runs a tiny trained integer predictor inside a 32 KiB native ROM. Three implementations share a 32-room synthetic world with mutable room state, A/B/D-pad controls and revisit checks. Each passed 1,028 exact-ROM scene checks; repeated builds match. The learned predictor has 640 weight bytes but needs repairs on 52 of 256 held-out sequences. The direct procedural baseline is smaller and faster. This is a bounded architecture experiment, not a commercial-game adaptation or an LLM on Game Boy Color. Source, three ROMs, emulator screenshots and reproducible commands are retained with the results.

## Run locally

Python 3.9+ and a C compiler suffice for host tests. Run from a checkout:

```sh
python3 -m unittest discover -s tests -v
python3 -m retrofy.cli identify /absolute/path/to/local/game
python3 -m retrofy.cli plan /absolute/path/to/board.xsb --out build/plan.json
```

Review **every field** of `build/plan.json`, especially declared rules, departures, control policy and unresolved evidence. The plan command prints its canonical SHA-256 approval token. Approval is explicit; it is not a confidence score or rights determination.

Create a local rights ledger (keep it and input files out of Git):

```json
{
  "access_basis": "Describe how this exact local material may be accessed",
  "adaptation_basis": "Describe applicable permission or other basis; ownership alone is insufficient",
  "redistribution": "Describe restrictions; default to private local use"
}
```

With GBDK-2020 **4.5.0** installed, set `GBDK_LCC` to its `bin/lcc` executable:

```sh
python3 -m retrofy.cli build /absolute/path/to/board.xsb \
  --plan build/plan.json --approve REVIEWED_PLAN_HASH \
  --rights local/rights.json --out build/unique-attempt
```

The output directory must not exist. Generated C, level data, logs, ROM, linker symbols and `record.json` stay local. `record.json` binds input, plan, generated source, compiler and ROM hashes. **It contains input-derived data and rights notes: do not publish it for proprietary inputs.** The ledger records assertions; the software does not validate legal rights. No DRM circumvention or proprietary-file upload is implemented.

For the included synthetic fixtures only:

```sh
PYTHONPATH=. python3 tools/build_fixtures.py build/fixture-run "$GBDK_LCC"
# Use a Python environment containing PyBoy==2.7.0 and Pillow==12.3.0:
PYTHONPATH=. python3 tools/emulator_check.py build/fixture-run/push build/check-push
```

Repeat the last command for `interactions` and `max-board`, choosing fresh output directories. The emulator script is fixture-oriented: it expects a nonempty solution and tests restart, one-level undo, victory and input policy. It is not a universal game evaluator. No wheel downloads or tool installation happen in these commands. [Toolchain provenance](docs/toolchains.md) describes the tested setup.

## Current boundaries

- One rectangular ASCII board; explicit wall perimeter; 3–20 columns, 3–16 rows; one player; 1–32 boxes; equal box/goal counts. Symbols: `# .@$*+` and space. No comments, multi-level packs, archives, scripts or executables accepted by the adapter.
- D-pad makes a cardinal move on a fresh press; no auto-repeat. A restarts immediately; B undoes the last successful move once. Blocked moves preserve undo. Multiple directions are ignored. A takes precedence over B and directions. No menus/chords required.
- Push exactly one box into an empty adjacent cell. Walls block movement; boxes cannot overlap. Win means every box lies on a goal. State remains playable after winning. No score, audio, save, story or original UI is preserved.
- A board needing cropping, reinterpretation or unknown semantics is rejected. Solver exhaustion is **unresolved**, never “unsolvable.” Search is capped at 100,000 states. The cap is a current algorithm limit, not a hardware limit.
- Build checks enforce ROM size, CGB header flag, ROM-only mapper and header checksum. Compilation does not establish hardware compatibility, fidelity or good gameplay. Compatible cartridge/flash hardware is needed to run a ROM on a stock Chromatic.
- Format hints and the `controls` prefilter route research and reject obvious mismatches; neither accepts an executable for conversion. Missing evidence remains unresolved.

Read [architecture and falsification experiments](docs/architecture.md), [benchmark protocol](docs/benchmarks.md), [evidence](evaluation/RESULTS.md), and [rights/access boundaries](docs/rights.md). The platform and original fixtures are MIT; that license grants no rights to user-supplied games.

## Steam library connection

Use the [private hosted connection](https://retrofy-steam.markizard.chatgpt.site) on your phone. No Mac is required. Revision 2 accepts no personal API keys and stores no library snapshots. Steam identity uses an encrypted, revocable one-hour cookie; server-side state is limited to pseudonymous challenges, rate counters and revocation metadata. Source and the threat model are under `hosted/`.

Library lookup requires an operator-managed Steam API key, currently not configured. Login is available; library sync remains disabled. The legacy local login entry points are disabled. [Setup and verification limits](docs/steam.md).

The current flagship research direction is [radical behavioral reconstruction](docs/ambition-first.md), working backward from BG3 rather than compressing its installation. [SteamOS index reconnaissance v2](hosted/intake/README.txt) is an input-analysis tool, not a game converter. Exact synthetic decision-graph and causal-state reductions include explicit negative controls and do not establish a BG3 compression factor.
