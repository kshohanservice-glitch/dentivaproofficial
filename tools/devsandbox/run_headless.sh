#!/usr/bin/env bash
# Run a command headlessly against the offscreen Qt platform.
#
#   tools/devsandbox/run_headless.sh python -m pytest -q
#   tools/devsandbox/run_headless.sh python -m dentivapro --check
#
# On a Windows machine (the product's target platform) this script is unnecessary: run the same
# command directly. It exists for bare Linux containers, where Qt's platform plugins link against a
# few desktop libraries that are not installed; see tools/devsandbox/README.md.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
stub_dir="$repo_root/tools/devsandbox/lib"

if [ ! -d "$stub_dir" ] || [ -z "$(ls -A "$stub_dir" 2>/dev/null | grep -v '^\.build$' || true)" ]; then
    echo "[devsandbox] building loader-only stub libraries (first run)…" >&2
    python3 "$repo_root/tools/devsandbox/make_stubs.py" >&2 || {
        echo "[devsandbox] could not build the stubs; run the command on Windows or install libgl1, \
libegl1, libxkbcommon0 and libdbus-1-3 on this host instead." >&2
        exit 70
    }
fi

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export QT_LOGGING_RULES="${QT_LOGGING_RULES:-qt.qpa.*=false}"
export LD_LIBRARY_PATH="$stub_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec "$@"
