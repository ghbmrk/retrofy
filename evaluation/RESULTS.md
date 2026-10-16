# Evaluation: 2026-10-15

**Working conformance prototype; zero existing-game conversions.** This report separates generated-fixture success from adaptation fidelity. No commercial or closed-source game bytes were supplied, executed or converted. No original-game equivalence or independent evaluator result exists.

| Dimension | Result | What it establishes |
|---|---|---|
| Conversion | Four original synthetic XSB fixtures generated four 32,768-byte CGB ROMs | One native backend can lower varying content in one declared mechanics family |
| Host conformance | 8 tests passed; 35,524 C-versus-Python transitions | Same movement and victory outcomes on enumerated/generated states; not original-game fidelity |
| Exhaustive states | Push: 306; interactions: 6,068; deadlock: 7; all four cardinal actions per state | Complete reachable movement coverage for these small synthetic boards only |
| Metamorphic | 100 seeded generated boards × 100 moves; horizontal reflection and left/right inversion | Coordinate symmetry; arbitrary interior walls and box collisions tested |
| Exact native ROM | 1,055 state/control checks over 5,917 emulator frames, PyBoy 2.7.0 CGB | Compiled code agrees with the specification on solution + seeded traces, undo/restart/blocked/held/conflicting inputs |
| Geometry/entity stress | 320 cells, up to 32 boxes in one ROM | Current structural maxima compile and pass exercised traces; not worst-case solver complexity |
| Update latency | Two injected-input-to-completed-update emulator frames on recorded solution moves | Frame-polled observation including emulator input scheduling; not CPU cycles or every possible move |
| Optimization | Max-board solution update went from 11 to 2 frames | Full-board snapshots and scanning were avoidable; delta undo and incremental goal count retained semantics |
| Memory/graphics | Static `_DATA` 683 bytes + 1 initialized; 19 HRAM; 160 shadow OAM; 128 tile bytes; zero sprites | Linker allocation and source-derived graphic use; stack high-water, transfer timing and CPU cycles remain unmeasured |
| Reproduction | All four exact ROM hashes repeated in a fresh directory, same macOS arm64/GBDK release | Same-host repeatability; cross-host reproducibility and independent reproduction remain untested |
| Human effort/feel | Not measured | No reduction-in-labor, comfort, fidelity or playability score claimed |
| Transfer | Zero held-out games; one mechanics family | Broad applicability remains open |
| Physical | Zero tests | No stock Chromatic/cartridge compatibility certification |

[Machine-readable summary](summary.json) binds all ROM hashes; [host records](host-tests.json) retain transition/state counts. Each fixture directory retains input/plan/source/compiler/ROM hashes, build log, emulator checks and genuine boot/solved frames. The public records contain only original MIT fixture content. ROM binaries remain under ignored local build directories; `tools/reproduce.py` builds and checks them against the published hashes.

The Python behavioral specification and C kernel were written separately but by the same development process. Shared misunderstandings remain possible. Host C and native SM83 compilation have different ABIs; exact-ROM checks mitigate this for exercised traces without proving all C states on hardware. Randomized tests are deterministic and reproducible, not statistically representative of all games.

## Failed experiments and limitations retained

- First native link failed because `reset` collided with a GBDK runtime symbol. It was renamed `reset_level`; no successful ROM was claimed for the failed attempt.
- First genuine framebuffer inspection revealed boot-background residue. Startup now explicitly clears the background map with LCD off; later frames were rechecked.
- First 320-cell update took 11 emulator frames despite small tile transfers: whole-state snapshots and scans scaled poorly. Reversible box/player deltas and incremental off-goal counts replaced them. No geometry/rule/entity cap was reduced to obtain the improvement.
- Full-board restart remains multi-frame; no one-frame restart guarantee is made. Observation quantization is too coarse for cycle claims.
- The deadlocked fixture is exhaustively unsolvable under the declared rules. Solver budget exhaustion is tested separately and returns unresolved.
- Direct executable recovery, isolated runtime capture, learned behavioral inference, semantic lifting beyond this grid family, CPU/stack measurement and physical deployment are absent. These are substantial remaining engineering/research tasks, not hidden completed stages.

The strongest next evidence would be a supplied, fingerprinted original game and preregistered behavioral traces. Another synthetic level cannot close that gap.
