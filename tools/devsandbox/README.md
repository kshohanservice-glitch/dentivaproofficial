# Development sandbox helpers

These scripts make the project's test suite runnable on a **bare Linux container** (the environment the
implementation agent works in). They are development conveniences only: nothing here is packaged,
shipped or referenced by the product, and the Windows build never uses them.

## The problem

Dentiva Pro's interface is Qt (PySide6). On Windows — the platform the product targets — everything
works out of the box. On a minimal Linux container that has Python and PySide6 but none of the desktop
libraries Qt's platform plugins link against, even the *offscreen* Qt platform fails to start:

```
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
```

## The recipe

```bash
# once per container: build loader-only stub libraries into tools/devsandbox/lib/
tools/devsandbox/run_headless.sh python -m pytest -q        # builds the stubs on first run

# or explicitly
python tools/devsandbox/make_stubs.py
tools/devsandbox/run_headless.sh python -m dentivapro --check
```

`run_headless.sh` sets `QT_QPA_PLATFORM=offscreen`, prepends `tools/devsandbox/lib` to
`LD_LIBRARY_PATH` and then runs the command you give it.

`make_stubs.py` reads the *undefined* symbols that the installed Qt libraries expect from
`libGL`, `libEGL`, `libxkbcommon` and `libdbus-1`, and compiles tiny no-op stubs that satisfy the
dynamic loader, including the symbol-version nodes Qt requires (`LIBDBUS_1_3`). No graphics, audio or
IPC work is performed — the tests never draw to a real display.

Requirements: `gcc`, `readelf` (binutils) and the project virtual environment with PySide6 installed.

## Honest limitations

* The stubs are **not** a substitute for a desktop stack. They exist so the same test suite can run in
  a headless container; screenshots produced there may differ from Windows in font hinting and
  anti-aliasing. Pixel-exact goldens are therefore validated on Windows CI, and the Linux run checks
  structure and rendering sanity (see `tests/ui/test_golden_screens.py`).
* If the environment already provides these libraries (a normal developer machine, or a CI runner with
  an X server), do not use this folder at all — run the tests directly.
* `--force` rebuilds the stubs; the Qt libraries themselves are never shadowed (a real
  `libQt6DBus.so.6` is used when present, because a stub cannot provide its complete ABI).

## Windows / normal developer machine

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
```
