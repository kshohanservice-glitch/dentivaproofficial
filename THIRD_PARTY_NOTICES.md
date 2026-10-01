# Third-Party Notices — Dentiva Pro

Dentiva Pro includes and depends on the third-party components listed below. Each component is used under
its own licence; the obligations recorded here are implemented in the product (notices shipped in
`src/dentivapro/assets/notices/`, displayed in About → Open-source notices, and reproduced in the
installer payload).

Full licence texts are added to `src/dentivapro/assets/notices/` in Phase 1 from the upstream distributions
(vendored at build time from the pinned package versions), and the font licences are already vendored in
`docs/licenses/`.

## Runtime components

| Component | Version | Licence | Purpose | Obligations met |
|---|---|---|---|---|
| Python | 3.12.x | PSF-2.0 | Application runtime | Copyright notice reproduced in notices |
| PySide6 / PySide6-Essentials / shiboken6 | 6.11.2 | LGPL-3.0 (Qt for Python) | UI, printing, PDF | Dynamic linking; Qt libraries remain separately replaceable files in the installed program folder; LGPL-3.0 text shipped; no modifications; upstream sources publicly available; the user's right to relink is preserved |
| Qt 6 (Core, Gui, Widgets, PrintSupport, Svg, Network) | 6.11.2 | LGPL-3.0 | UI framework and print engine | Same as above; Qt copyright notices reproduced |
| argon2-cffi / argon2-cffi-bindings / libargon2 | 25.1.0 / 26.1.0 | MIT / Apache-2.0 OR CC0-1.0 | Password hashing (Argon2id) | MIT and Apache-2.0 notices reproduced |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | Optional encrypted backups, HMAC signatures for activation state | Apache-2.0 notice and OpenSSL notice reproduced |
| cffi | 1.17+ | MIT | Binding runtime for argon2-cffi | MIT notice reproduced |
| pycparser | 2.22+ | BSD-3-Clause | cffi dependency | BSD notice reproduced |
| platformdirs | 4.12.2 | MIT | Windows data directories | MIT notice reproduced |
| segno | 1.6.6 | BSD-3-Clause | Offline QR codes on printed documents | BSD notice reproduced |
| Inter (font) | 4.x variable | SIL OFL-1.1 | UI/Latin typography | Vendored unmodified with `OFL-1.1-Inter.txt`; not sold standalone; reserved font name respected |
| Noto Sans Bengali (font) | 2.x variable | SIL OFL-1.1 | Bengali shaping | Vendored unmodified with `OFL-1.1-NotoSansBengali.txt`; not sold standalone |
| Lucide icons (SVG subset) | pinned | ISC | UI iconography | ISC notice reproduced |
| Microsoft Visual C++ runtime libraries | bundled with CPython | Microsoft redistribution terms | Native runtime DLLs | Redistributed under Microsoft's redistribution rights for the CPython distribution |

## Build- and test-only components (not shipped)

| Component | Licence | Use |
|---|---|---|
| PyInstaller | GPL-2.0 with the PyInstaller bootloader exception | Producing the Windows bundle; the exception explicitly permits building and distributing proprietary applications |
| NSIS | zlib/libpng | Producing the installer |
| pytest, pytest-qt, pytest-cov, pytest-timeout, pytest-benchmark | MIT | Automated testing |
| ruff | MIT | Linting/formatting |
| mypy | MIT | Static type checking |
| pypdf | BSD-3-Clause | PDF verification in tests |
| Pillow | MIT-CMU | Image comparison in UI golden tests |
| coverage | Apache-2.0 | Coverage measurement |

## Attribution statements

- **Qt / PySide6:** "This software uses the Qt toolkit and PySide6 under the GNU Lesser General Public
  License, version 3. Qt is a trademark of The Qt Company Ltd. and is used here in accordance with the
  LGPL's nominative-use permission."
- **Fonts:** "Inter and Noto Sans Bengali are used under the SIL Open Font License 1.1."
- **Argon2:** "Password hashing uses the Argon2 reference implementation (Argon2id) via argon2-cffi."

## Zero-cost verification

No component in the runtime list requires a paid licence, a subscription, a cloud account or network
access. This was verified during Phase 0 by resolving every production wheel for Windows and reviewing each
licence; `tools/qa/check_licenses.py` (Phase 1) re-validates the pin set in CI and fails the build if a
component with an incompatible or undeclared licence appears.
