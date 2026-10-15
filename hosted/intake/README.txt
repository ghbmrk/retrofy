RETROFY LOCAL INTAKE v1

SteamOS Desktop Mode, Python 3, and KDialog or Zenity required.
No administrator access. No installer. No network client. No Steam login required.

1. Extract the downloaded archive using Ark / Extract Here.
2. Open the extracted Retrofy-Intake folder.
3. Open Retrofy-Intake.desktop (Retrofy Local Intake).
   KDE may ask you to confirm launching this downloaded application.
   Only run the package downloaded from your private Retrofy site.
   Alternatively open the executable Retrofy-Intake.sh and choose Execute.
   If permissions are lost: Properties > Permissions > Is executable.
4. Read the local confirmation, then choose Yes to inspect BG3.
5. The tool automatically locates Steam libraries. If necessary, choose BG3's folder.
6. A NEW Retrofy-Report-* folder appears on Desktop, or home if Desktop is absent.
   Read report.json before sharing. Nothing uploads automatically.

The launcher runs the included intake.py with Python. All source is readable.
No accounts, credentials, saves or userdata are scanned. Only a whitelisted Steam
build ID and app ID enter the report. Archive records contain safe labels, sizes,
format hints and hashes of the first 4096 bytes; full-file integrity is NOT verified.
Unrecognized archive names are replaced with generic labels.
Game archives are not extracted and their raw header bytes are not included.
Mods and adaptation rights are unassessed. No conversion is performed.

This package has been tested with synthetic installations. It has not yet been
run on your Steam Machine. KDE launch behavior can vary with desktop settings.
Cancellation writes no report; success creates new files only. Existing game
files and existing report folders are not modified.
