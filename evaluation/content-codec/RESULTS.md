# Exact content codecs and a measured native frontier

The [experimental loop](../../docs/experimental-loop.md) has now completed a second native experiment. This tests lossless visual-content reconstruction, not game recovery. All content is original synthetic data. No proprietary files, user IDs or Steam credentials are included.

**Decision:** keep authoritative gameplay state separate from content generation; select codecs by measured domain and latency. Use a fitted patch dictionary where motifs repeat, bit packing where they do not. No neural advantage or BG3 adaptation is established.

## Frozen question and failure gates

Can a representation fitted only on training scenes reconstruct every tile of unseen scenes without a semantic repair implementation, while fitting a native GBC runtime? Compare complete implementations of raw tiles, 3-bit packing, RLE, bounded-window LZ back references and a fitted 4-by-3 patch dictionary. A sixth variant stores dictionary entries unpacked to test the size/time tradeoff.

Before native evaluation, the contract was exact reconstruction, preservation of the existing native state/revisit kernel, full regeneration within four emulator frames, cached updates within two, and no post-startup LCD blanking. Missing physical/human evidence remains unresolved even when those technical gates pass. Smallest data payload alone cannot win.

Each corpus contains 32 scenes of 20-by-18 symbols, with five decorative tile choices. Rooms 0–23 fit the dictionary; rooms 24–31 are held out. The dictionary is frequency fitted and conventional, not an LLM or neural network. Novel patches use exact literal escapes; their bytes are counted. No per-test-scene manual patch or canonical-answer validator is used by the codec.

- **Shared:** 24 reusable motifs plus two unique blocks in every scene; held-out scenes recombine familiar motifs and retain their unique blocks.
- **Novel:** exactly the same training scenes/codebook, but all held-out blocks use unfamiliar content.
- **Entropy control:** independently sampled symbols under a fixed pseudorandom generator. It is difficult for these tested codecs, not an information-theoretic incompressibility proof. A generator aware of the fixture's seed could encode it differently; that possibility is not a result for real authored content.

The five-symbol vocabulary and aligned 4-by-3 motif construction favor the matching dictionary. This is an explicit mechanism test, not an unbiased sample of commercial art. Corpus hashes, source hashes and split are in [builds.json](builds.json). The generator and integer codec choices are frozen in source and reproducible without downloads.

## Native results

All physical ROMs occupy **32,768 bytes**, use ROM-only cartridges with no SRAM, and declare **CGB-only** operation (header 0xC0). Linked extent measures occupied ROM address range, including code, data, fonts and header gaps; it is not a smaller cartridge size.

| Corpus | Selected under four-frame budget | Linked ROM extent | Full update | Cached update |
|---|---|---:|---:|---:|
| Shared | Packed patch dictionary | 8,653 B | 4 frames | 1 frame |
| Novel | Packed patch dictionary, whole corpus | 9,773 B | 4 frames | 1 frame |
| Entropy control | 3-bit packing | 11,224 B | 3 frames | 1 frame |

The packed baseline uses 11,224 linked bytes for every corpus. The shared dictionary saves 2,571 linked bytes (22.9%) against that baseline, at a cost of one additional full-update frame. Raw tiles use 18,250 linked bytes and update within two frames. The measured frontier therefore offers explicit size/latency choices; there is no universally best codec.

**Held-out failure matters:** on novel scenes, patch payloads require 1,440 bytes versus bit packing's 1,080. The whole mixed corpus still favors patches because its training portion shares motifs. That is not a compression win on unfamiliar motifs. On the entropy control, the packed-patch implementation uses 13,014 linked bytes and is dominated by bit packing.

The unpacked-dictionary variant is faster on shared decoding at coarse timer resolution, but does not reduce the four-frame worst case and increases linked size. Its worst decoding time worsens on novel literals. RLE and LZ also fail to beat the measured frontier in this domain. [selection.json](selection.json) records every variant and the deterministic selector; selection means a synthetic representation candidate, never a successful adaptation.

## Hardware-aware iteration

The first decoder redundantly mapped symbols in a second pass. One render timer overflowed; that sample is invalid as a cycle estimate. Removing the second pass, using pointer increments and unrolling fixed 3-bit groups preserved exactness. With the old display path, the next iteration still required six to eight frames and temporarily disabled the LCD. Those failures are retained in [earlier-iterations](earlier-iterations).

The final display path prepares a padded 576-byte tilemap in WRAM, then performs CGB general-purpose VRAM DMA during VBlank. The source is aligned to 16 bytes. HUD and player marker are included in that commit. Startup uses the console font once to recover its actual tile encoding; regeneration no longer calls formatted console output. Cached movement changes two tiles. The display stays enabled after initialization in source and every sampled post-ready frame.

[Pan Docs' CGB registers](https://github.com/gbdev/pandocs/blob/master/src/CGB_Registers.md) document DMA restrictions and 16-byte blocks. Measured native start/end scanlines were 146/147 for every checked transfer. This is emulator evidence; physical timings and human comfort are untested. The guarded transfer requires CGB hardware and is not a DMG fallback.

Each final ROM has 1,157 bytes of linker-allocated static data/HRAM, including the 591-byte alignment allocation and font map, plus separately reserved shadow OAM and unmeasured stack. Custom art occupies 20 tiles/320 bytes; console-font VRAM was not separately profiled. No OAM sprites, audio or bank switching are used. No general capacity claim follows from this tiny corpus.

## Verification and what it establishes

- **18 exact ROMs × 1,028 scenes = 18,504 native scene checks.** Each compares eight facts and all 360 reconstructed tiles against an independent Python reference. VRAM is additionally checked for every scene, including HUD and player placement.
- Each ROM's actual controller replay opens a chest, gains a key, changes another room's NPC state and returns. Changes persist in volatile WRAM. Seeded tests cover all 1,024 room/flag/key combinations plus key-gated exits and conflicting/held input. No power-cycle save is claimed.
- Host C checks cover 32 unoverlaid backgrounds and 1,024 overlaid contexts per variant. Full backgrounds include cells later hidden by borders/HUD, so a rendering overlay cannot conceal a codec mismatch.
- 720 different-seed, single-symbol metamorphic cases produce 1,440 exact host round trips. One source-symbol change remains exactly one decoded-symbol change. These are codec-family checks, not cross-game transfer.
- Across 102,030 sampled post-ready emulator frames, LCD enable remained set. All checked DMA transfers completed during VBlank. Sampling is not a continuous physical trace; source and scanline records supply separate evidence.
- No final render/upload timer overflow occurs. Timing uses coarse emulated hardware counters at 1,024 T-cycles per tick with interrupt overhead. Full-update frame counts include decoding, overlays, staging and transfer; they are not real-device response measurements.
- All 18 second builds match their first ROM hashes on the same host. [Reproducibility records](reproducibility.json), linker maps, build logs, ROMs and per-variant checks are retained. The remaining compiler warnings are constant-flow/unreachable-code optimization in the procedural-only kernel, whose state outputs are checked exhaustively over the declared domain.
- The platform's 18 existing tests also pass. Python and C implementations were authored in the same project; an independent evaluator has not repeated this work.

## Reproduce

Use the authenticated [toolchain](../../docs/toolchains.md), a POSIX host, C compiler and Python environment containing PyBoy 2.7.0/Pillow. Choose an unused output directory:

```sh
python experiments/content_codec/run.py \
  --out build/content-reproduction --lcc /path/to/gbdk/bin/lcc
```

The runner builds, checks, repeats and selects. Its constituent commands were executed for this record; output folders are retained locally. No user-game installation, account, network runtime or new Steam Machine action is required. Selected ROM folders retain generated source and screenshots; every variant retains its ROM, linker map, build log and checks. [builds.json](builds.json) binds exact generated-source hashes for every build.

## Next loop, with a stopping rule

The visual codec uncertainty has a bounded result. Do not scale this motif fixture to suggest BG3 feasibility. Next, freeze a small causal content-program interface that separates conditions, effects, persistent variables, authored text and scene cues. Test identical present screens with different delayed outcomes; then compile a dependency-complete branch/revisit scenario with exact unique content. Compare bytecode, decision graphs and specialized native functions on total bytes and worst-case execution. Refuse any abstraction that merges states with different preserved futures.

The earlier [causal quotient experiment](../../docs/ambition-first.md#completed-causal-state-experiment) already gives a complete finite counterexample to screen-only state merging. The missing advance is compositional native execution and recovery from actual game materials. Before asking for more Steam Machine work, define a bounded extractor output that answers those questions and can be collected once. Archive headers alone cannot supply that evidence.

No recovered BG3 rule, commercial-game conversion, automatic semantic inference, human-effort reduction per real adaptation, independent evaluation or physical Chromatic result is claimed. No human interaction with the separate Steam Machine was needed for this experimental loop.
