#!/bin/sh
# Optional executable entry point. No downloads, administrator access or installation.
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
if command -v python3 >/dev/null 2>&1; then
    exec python3 "$base/intake.py"
fi
message='Retrofy needs Python 3, which is not available. Nothing was installed, changed or uploaded.'
if command -v kdialog >/dev/null 2>&1; then
    kdialog --msgbox "$message"
else
    printf '%s\n' "$message"
fi
exit 1
