#!/usr/bin/env python3
"""Build loader-only stub libraries so Qt's offscreen platform starts on a bare Linux host.

Why this exists
---------------
Windows is the product's only supported platform, and the automated build/validation of the Windows
executable happens on GitHub Actions ``windows-latest`` runners, where none of this is needed.

Developers (and automated checks) sometimes need to run the Qt test suite on a *bare* Linux
container that has Python and PySide6 but none of the desktop libraries Qt's platform plugins link
against (``libEGL``, ``libGL``, ``libxkbcommon``, ``libdbus-1``, ``libQt6DBus``). Without them even
``QT_QPA_PLATFORM=offscreen`` fails at import time with "cannot open shared object file".

This tool reads the *undefined* symbols that the installed Qt libraries expect from those libraries
and writes tiny no-op stubs for exactly those symbols, so the dynamic loader is satisfied. The stubs
are loader-only placeholders: they perform no graphics, audio or IPC work. They are **not** part of
the product, never shipped, and never included in an installer; they exist so the same test suite can
run on a machine that has no display stack at all.

The generated files are written to ``tools/devsandbox/lib/`` (git-ignored). ``run_headless.sh`` calls
this script automatically when the directory is missing.

Requires: ``gcc``, ``readelf`` (binutils) and an installed PySide6.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE / "lib"

#: library soname -> regular expression matching the symbols it must provide
TARGETS: dict[str, str] = {
    "libGL.so.1": r"^(gl|glX|glx|__gl)",
    "libEGL.so.1": r"^egl",
    "libxkbcommon.so.0": r"^xkb",
    "libdbus-1.so.3": r"^dbus_",
}

#: Qt loads this library when it is present; PySide6-Essentials does not ship it. Any symbol the
#: other Qt libraries or plugins request from it is stubbed.
OPTIONAL_QT_LIBS = ("libQt6DBus.so.6",)


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _qt_root() -> Path:
    """The ``PySide6/Qt`` directory of the installed PySide6."""
    try:
        import PySide6  # noqa: PLC0415 - optional dependency of this developer tool
    except ImportError as exc:  # pragma: no cover - developer tool
        raise SystemExit(
            "PySide6 is not importable. Create the project virtual environment first "
            "(see tools/devsandbox/README.md)."
        ) from exc
    root = Path(PySide6.__file__).resolve().parent / "Qt"
    if not root.is_dir():  # pragma: no cover - defensive
        raise SystemExit("Could not locate PySide6's Qt libraries.")
    return root


def _qt_library_dir() -> Path:
    """The directory holding Qt's shared libraries (``libQt6*.so``)."""
    root = _qt_root()
    for candidate in (root / "lib", root):
        if candidate.is_dir():
            return candidate
    raise SystemExit("Could not locate PySide6's Qt libraries.")  # pragma: no cover


def _qt_files() -> list[Path]:
    """Every Qt shared library and plugin that may request symbols from a stubbed library."""
    return sorted(path for path in _qt_root().rglob("*.so*") if path.is_file())


def _undefined_symbols(paths: list[Path]) -> set[str]:
    symbols: set[str] = set()
    for path in paths:
        try:
            output = _run(["readelf", "--dyn-syms", "-W", str(path)])
        except RuntimeError:
            continue
        for line in output.splitlines():
            if " UND " not in line:
                continue
            parts = line.split()
            if len(parts) >= 8:
                name = parts[7].split("@")[0]
                if name:
                    symbols.add(name)
    return symbols


def _defined_symbols(path: Path) -> set[str]:
    try:
        output = _run(["readelf", "--dyn-syms", "-W", str(path)])
    except RuntimeError:
        return set()
    found: set[str] = set()
    for line in output.splitlines():
        if " UND " in line:
            continue
        parts = line.split()
        if len(parts) >= 8:
            found.add(parts[7].split("@")[0])
    return found


def _required_version_nodes(soname: str) -> list[str]:
    """Symbol-version nodes that Qt's own libraries expect from *soname* (usually ``Qt_6``).

    Qt's shared libraries are versioned: a requester will not accept an unversioned symbol from a
    library that should provide a version node. Building the stub without the node makes the dynamic
    loader abort with an assertion, so the nodes are read from the installed Qt and reproduced.
    """
    nodes: set[str] = set()
    for path in _qt_files():
        try:
            output = _run(["readelf", "--version-info", str(path)])
        except RuntimeError:
            continue
        relevant = False
        for line in output.splitlines():
            if "File:" in line:
                relevant = f"File: {soname}" in line
                continue
            if relevant and "Name:" in line:
                # ``  0x0130:   Name: Qt_6  Flags: none  Version: 7``
                parts = line.replace(":", " ").split()
                if "Name" in parts:
                    index = parts.index("Name")
                    if len(parts) > index + 1:
                        nodes.add(parts[index + 1])
    return sorted(nodes)


def _compile(soname: str, symbols: list[str], *, version_nodes: list[str] | None = None) -> Path:
    """Write and compile a stub library exporting *symbols* as no-ops."""
    build = LIB_DIR / ".build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / f"{soname}.c"
    version_script = build / f"{soname}.map"
    source.write_text(
        "#include <stddef.h>\n#include <stdint.h>\n"
        + "".join(f"void *{symbol}(void) {{ return NULL; }}\n" for symbol in symbols),
        encoding="utf-8",
    )
    command = ["gcc", "-shared", "-fPIC", f"-Wl,-soname,{soname}"]
    if version_nodes:
        entries = [f"{version_nodes[0]} {{ global: *; }};"]
        entries += [f"{node} {{ }};" for node in version_nodes[1:]]
        version_script.write_text("\n".join(entries) + "\n", encoding="utf-8")
        command.append(f"-Wl,--version-script={version_script}")
    output = LIB_DIR / soname
    command += ["-o", str(output), str(source)]
    _run(command)
    return output


def build(*, force: bool = False) -> int:
    """Create the stub libraries; returns the number of libraries written."""
    for tool in ("gcc", "readelf"):
        if shutil.which(tool) is None:
            raise SystemExit(
                f"'{tool}' is required to build the stub libraries. On a normal developer machine "
                "these stubs are unnecessary — run the tests on Windows or on a CI runner that has "
                "an X server / libgl1-mesa installed instead."
            )

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    qt_files = _qt_files()
    if not qt_files:  # pragma: no cover - defensive
        raise SystemExit("No Qt libraries found; is PySide6 installed in this environment?")

    requested = _undefined_symbols(qt_files)
    written = 0

    for soname, pattern in TARGETS.items():
        matcher = re.compile(pattern, re.IGNORECASE)
        symbols = sorted(symbol for symbol in requested if matcher.match(symbol))
        if not symbols:
            print(f"{soname:<22} nothing requested (host may already provide it)")
            continue
        target = LIB_DIR / soname
        if target.exists() and not force:
            print(f"{soname:<22} already present ({len(symbols)} symbols)")
            continue
        _compile(soname, symbols, version_nodes=_required_version_nodes(soname))
        print(f"{soname:<22} {len(symbols)} symbols")
        written += 1

    for soname in OPTIONAL_QT_LIBS:
        real = _qt_library_dir() / soname
        if real.exists():
            # Never shadow a real Qt library: a stub would miss symbols Qt needs (a forced stub of
            # Qt6DBus, for example, makes Qt fail to load). Only a genuinely absent library is stubbed.
            print(f"{soname:<22} provided by PySide6 (no stub needed)")
            continue
        # Symbols that other Qt libraries/plugins must resolve from this soname: everything they
        # leave undefined that no other Qt library in the installation provides.
        provided_elsewhere: set[str] = set()
        for candidate in qt_files:
            provided_elsewhere |= _defined_symbols(candidate)
        missing = sorted(
            symbol
            for symbol in _undefined_symbols(qt_files)
            if symbol.startswith("_Z") and symbol not in provided_elsewhere
        )
        if not missing:
            print(f"{soname:<22} nothing to stub")
            continue
        _compile(soname, missing, version_nodes=_required_version_nodes(soname))
        print(f"{soname:<22} {len(missing)} symbols")
        written += 1

    print(f"\nStub libraries in {LIB_DIR}")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rebuild even when files exist")
    args = parser.parse_args()
    build(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
