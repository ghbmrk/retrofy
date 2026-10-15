# Toolchains and hardware boundary

The development session used the installed ModRetro Chromatic plugin's **packaged setup workflow**, which authenticated and prepared GBDK-2020 4.5.0, official GB Studio CLI 4.3.2 and a managed PyBoy 2.7.0/Pillow 12.3.0 environment. The session did not expose the plugin's authoring/emulator/device MCP tools. Direct GBDK builds and public PyBoy APIs were used after setup. No GB Studio project/editor integration, browser preview, cartridge flashing or physical test is claimed.

This platform intentionally emits standalone C: its contract kernel and state symbols are explicit, and its host differential tests compile the same C source. GB Studio remains an alternative for conventional scene/event games; forcing recovered semantics into visual events could conceal bespoke engine work. RGBDS offers assembly control for measured hot paths, banking and cycle-sensitive routines; it adds implementation cost and is not yet used or benchmarked. GBDK is the first backend, not a claim that C always meets hardware budgets.

Tested release archive: [GBDK 4.5.0 macOS arm64](https://github.com/gbdk-2020/gbdk-2020/releases/download/4.5.0/gbdk-macos-arm64.tar.gz), SHA-256 `289ee60e46c5a2785a21e35533f84a5131ed4a063b21b0dbdedc9a10af15bf78`. Compiler `lcc` SHA-256 `c610f19ea2c602127c1c23b45f57d15048d7600c40e194bc1b209a2145d57d01`. Hashing the driver alone does not pin SDCC, libraries or the linker; preserve and authenticate the entire release archive. Other hosts need their own authenticated official archives; cross-host identical ROMs have not been tested.

## Budgets

[Pan Docs](https://gbdev.io/pandocs/) and [GBDK's toolchain documentation](https://gbdk.org/docs/api/docs_toolchain.html) are primary references. Frame timing is approximately 59.73 Hz, not exactly 60. [VRAM access restrictions](https://gbdev.io/pandocs/Rendering.html) depend on LCD mode. The GBC has 32 KiB WRAM and 16 KiB VRAM; OAM holds 40 objects with at most 10 selected per scanline. These hard limits differ from this implementation's conservative caps.

The backend uses only bank 0, eight monochrome-pattern tiles with a CGB palette (128 tile bytes), one background map, no OAM sprites, no audio, no SRAM, and a 32 KiB ROM-only cartridge configuration. Current board cap is 20×16; this is a readability/layout choice, not total world-size capacity. No mapper or bank switching is implemented. [GBDK MBC support](https://gbdk.org/docs/api/docs_rombanking_mbcs.html) does not prove any particular physical flash cartridge supports the chosen ROM; that must be tested independently.

Each ordinary move touches at most three board tile IDs plus one victory tile. Rejected movement may write two identical board positions plus the victory tile. Undo is also a delta. Reset scans the full board and can take multiple frames. Initial tilemap clear occurs with LCD off. GBDK tile routines handle safe VRAM access; this does not establish vblank-only transfers or tear-free presentation under every workload.

The final crowded-board linker allocation has 683 bytes `_DATA` plus 1 initialized byte, 160 bytes reserved shadow OAM and 19 bytes HRAM. This is **static linker allocation**, not measured stack/total RAM high-water. CPU cycles, transfer timestamps and scanline stress have not been profiled. Two emulator frames from injected input to completion include emulator input scheduling and frame-boundary polling; they are not a CPU-time measurement. See retained exact-ROM records.

Reproduce from a checkout with authenticated GBDK and Python containing PyBoy 2.7.0/Pillow 12.3.0:

```sh
python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 tools/build_fixtures.py build/reproduction "$GBDK_LCC"
PYTHONPATH=. python3 tools/emulator_check.py build/reproduction/crowded build/crowded-check
```

Repeat builds into fresh directories and compare `rom_sha256` values. Fixture records have no user-owned material. Run physical tests only using an identified compatible cartridge: retain cartridge model/firmware, Chromatic firmware/hardware revision, exact ROM hash, recording, workload and input sequence. PC-emulated video streamed to Chromatic is not native cartridge execution evidence.
