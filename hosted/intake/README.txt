RETROFY BG3 INDEX ANALYSIS v2.0.0

Run on the SteamOS machine containing your installed BG3.
Python 3 + KDialog or Zenity required. No installer, administrator access or network client.

1. Download Retrofy-BG3-Index-v2.tar.gz from your private Retrofy /intake page.
2. In Ark, extract ALL FILES, not just the selected launcher.
3. Open the new Retrofy-BG3-Index-v2 folder. There must be SIX files:
   Retrofy-Intake.desktop, Retrofy-Intake.sh, intake.py, lspk.py, README.txt, LICENSE-LSLIB.txt.
4. Open Retrofy-Intake.desktop (Retrofy BG3 Index Analysis). Confirm launch if KDE asks.
   Alternatively execute Retrofy-Intake.sh. If permissions were lost, use
   Properties > Permissions > Is executable. No command typing is required.
5. Read and accept the local scan confirmation. Steam libraries are found automatically.
6. Allow about two minutes. A NEW Retrofy-Report-* folder opens on Desktop or home.
   Open SUMMARY.txt for a short result, report.json for details. Nothing uploads.

READ SCOPE
Only installation metadata, 40-byte archive header probes and bounded v18 directory indexes.
LZ4 index metadata is decoded in memory. No indexed entry payload, text dialogue, script,
texture or audio is read, extracted, decoded or executed. Signature/header probes of
unrecognized files may read their first 40 bytes; no raw bytes enter the report. No saves, userdata or Mods scan.
No files in the installation are modified. Only a NEW private report folder is written.

REPORT PRIVACY
Whitelisted app/build IDs, archive labels, sizes and partial hashes. Internal archive
paths remain transient in memory; none enter the report. Unknown archive labels are
replaced. No account IDs, absolute paths or raw archive/header/index bytes are output.
Sharing a report or photo is a separate manual choice.

LIMITATIONS
LSPK v18 non-solid indexes only. Unknown/solid/oversized/malformed indexes, absent
parts and errors remain explicitly unresolved. Limits: 32 MiB packed, 128 MiB decoded,
400,000 entries per index; 256 MiB index reads per run; 45 seconds per index and
120 seconds total parser work (blocking filesystem I/O is not forcibly timed out).
Resource limits are tool limits, NOT Chromatic limits or incompatibility judgments.

Counts are filename-based candidates, not recovered gameplay semantics. Physical
patch records/duplicates are counted; actual load order and content dependencies
are unresolved. Partial hashes are NOT full-file verification. This is not a converter
or a prediction of GBC ROM size. No BG3 compression ratio is claimed.

FORMAT REFERENCES / ATTRIBUTION
Independent implementation based on public format layouts and LZ4 specification:
https://github.com/Norbyte/lslib/tree/6f5f6987d10d8485876b8368431c948e4dea4f83/LSLib/LS
https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md
LSLib's MIT notice is included for attribution; no LSLib runtime is bundled.
Tests use original synthetic archives and an independent test-only LZ4 codec.
No actual BG3 archive index has yet been evaluated by this version.
