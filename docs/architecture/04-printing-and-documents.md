# Dentiva Pro — Printing, PDF and Document Rendering Architecture (Phase 1)

Printing is a first-class subsystem, not a side effect of a screen. This document defines the engine,
templates, paper handling, preview, failure behaviour, determinism rules and test matrix.

---

## 1. Engine decision

**Qt print pipeline:** `QTextDocument` (rich text/HTML subset) rendered to `QPrinter` (HighResolution,
300 dpi) for the printer and to `QPdfWriter` for PDF, with `QPrintPreviewWidget` for preview.

Why:
- Single render path for preview, printer and PDF ⇒ the preview *is* the output (no divergence).
- Uses the Windows print system directly: any installed printer (USB, network/Wi-Fi, Bluetooth-via-Windows,
  thermal receipt printers, "Microsoft Print to PDF") works through the OS, with the native printer
  dialog when needed.
- Fully offline, no licence cost, no HTML-to-PDF service, no headless browser.
- Deterministic: the same document model + the same profile produces byte-identical page geometry.
- Bengali rendering verified in this environment with bundled fonts (shaping, conjuncts, ৳).

Rejected: HTML→PDF services (online, forbidden), wkhtmltopdf/Chromium (blocked in build env, heavier,
weaker Windows printer integration), ReportLab (a second layout engine = doubled print test surface,
weaker RTL/Indic text layout), Windows XPS/WPF printing (no .NET toolchain reachable; less control).

---

## 2. Document model

`printing/models.py` defines immutable value objects independent of the UI and the database:
`ClinicLetterhead`, `DentistBlock`, `PatientBlock`, `ClinicalSections` (C/C, O/E, Dx, R/E/Advice),
`MedicineTable`, `InvoiceTable`, `PaymentSummary`, `FooterBlock`, `DocumentMeta` (codes, dates,
verification string), each with a `*_snapshot`-friendly JSON form. Services produce these from the
persisted **snapshot columns** of the document (see the data model), so a reprint of a 2027 prescription
in 2031 looks exactly as it did — even if the clinic was renamed, the dentist's qualifications changed or
a treatment price was edited.

---

## 3. Print profiles

`print_profile` rows (managed in Settings → Printing) define: `kind` (prescription | invoice | report |
thermal-receipt), `paper` (A4, A5, A6, Letter, 80 mm roll, 58 mm roll, Custom W×H mm), `orientation`,
margins (mm per side), `base_font_pt`, `scale_percent`, `show_logo`, `show_qr`, `signature_height_mm`,
`copies`, `header_variant`, `is_default`. Profile data is validated (margins sane, font ≥ 7 pt, signature
area ≥ 22 mm) and shipped with three defaults: *Prescription A4*, *Prescription A5*, *Invoice A4*, plus
*Receipt 80 mm* and *Receipt 58 mm* variants.

Layout is built with **mm units** converted at print resolution, so a 15 mm margin is 15 mm on every
printer; text sizes are in points, not pixels, so nothing "shrinks into unreadable text".

---

## 4. Templates

### 4.1 Prescription (premium clinical)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [logo]  Sunrise Dental Care                       Dr. Shohan Khan           │
│         House 12, Road 5, Dhanmondi, Dhaka        BDS, MDS (Oral Surgery)   │
│         Phone: 01711-XXXXXX                       Consultant Dental Surgeon │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Patient: রহিম উদ্দিন            Age/Sex: 34 / Male      Date: 01 Oct 2026   │
│ Code: P-000042                  Phone: 01712-XXXXXX     Rx: RX-2610-00118   │
│ ─────────────────────────────────────────────────────────────────────────── │
│ C/C (Complaints)      : দাঁতের ব্যথা, swelling                    [chips]   │
│ O/E (On Examination)  : caries 36, gingivitis                     [chips]   │
│ Dx / R/E & Advice     : pulpitis 36 → RCT advised; warm saline rinses       │
│ Teeth: 36, 37                                                                │
│ ─────────────────────────────────────────────────────────────────────────── │
│  #  Medicine            Form     Strength   Dose(M-N-N)  Food    Duration   │
│  1  Napa                Tablet   500 mg     1 - 0 - 1     after   5 days     │
│  2  ফ্ল্যাগিল           Susp.    200 mg/5ml 1 - 1 - 1     after   7 days     │
│     Instruction: take after meals, complete the full course                 │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Follow-up: 08 Oct 2026                                                      │
│                                                                             │
│                        (≥ 22 mm blank area reserved for a manual signature) │
│                                          ______________________________     │
│                                          Dr. Shohan Khan, BDS, MDS          │
│                                          BMDC Reg. No. A-12345             │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Clinic hours: Sat–Thu 10:00–14:00, 17:00–21:00 · Closed Friday              │
│ This prescription is valid for the named patient only.  [QR: DOC-9f2c…]     │
└─────────────────────────────────────────────────────────────────────────────┘
```
Rules: the letterhead shows the clinic identity and the prescribing dentist with **all** designations and
**all** qualifications (wrapped, never truncated); the medicine table never splits a row across pages and
repeats its header per page; the signature block is a fixed-height footer that keeps a ≥ 22 mm blank area
above the printed signature line even on overflow pages; Bengali and Latin text mix freely.

### 4.2 Invoice
Header contains only clinic name, logo, address and phone (no prescription signature/footer structure).
Body: itemised lines (description, quantity, unit price, line total), subtotal, discount, surcharge,
total, amount paid, balance due, payment history table (date, method, reference, amount, received by),
and an unmistakable status stamp: **PAID / PARTIALLY PAID / UNPAID / VOID**. Footer: payment terms note
(configurable), optional QR of the document verification string, "computer-generated document" line.
Multiple pages repeat the header and the column headers and print a running total on each page.

### 4.3 Thermal receipts (58 / 80 mm)
A dedicated compact template rather than a scaled A4: 32/48-character-friendly typography, single column,
no side-by-side blocks, monospace amounts, a 5 mm-safe margin, and an optional cut-friendly trailing
blank feed. Verified against a simulated 58 mm and 80 mm page size.

### 4.4 Reports
Landscape A4 by default, repeating header, page numbers, filter summary in the header, totals row,
and a generated timestamp + user stamp.

---

## 5. Rendering pipeline

```
service → DocumentModel (from persisted snapshots)
        → TemplateRenderer (HTML subset + inline CSS, mm/pt units)
        → QTextDocument (fonts: Inter + Noto Sans Bengali, explicit fallbacks)
        → PrintProfile (page size, margins, scale)
        → ├── QPrintPreviewWidget → user previews pages exactly as printed
            ├── QPrinter (real printer, native dialog for device-specific options)
            └── QPdfWriter (offline PDF, no service, embedded fonts)
        → print event recorded (audit: document type, code, profile, copies, outcome)
```

Qt's rich-text engine supports the sub-set we need (tables with borders/padding, inline styles, images,
page breaks, alignment, colours). Anything the engine cannot express is constrained in the template
layer — templates never emit CSS that Qt silently ignores (a lint test parses template CSS and rejects
unsupported properties, so "it looked right in code but not on paper" cannot happen).

**Pagination and orphan control:** sections are emitted as non-splitting table rows and explicit
`page-break` blocks; the medicine/invoice tables repeat header rows; a footer block is emitted with a
forced page break when remaining space is below the block height (computed from the profile), which is
what guarantees the signature area can never collapse.

---

## 6. Paper, printer and failure handling

| Situation | Behaviour |
|---|---|
| Printer capability probe | `QPrinterInfo` reports available printers and `supportedPageSizes()`; profiles are matched to the closest supported size |
| Requested paper not supported by the device | A modal explains exactly what happened ("HP LaserJet M1136 does not report A5 support. Print on A4 with the A5 layout centred, or choose a supported size."), offering: print on a supported size with scaled layout, choose another printer, or cancel. **Never** silently produce a broken document |
| Printer offline / queue stuck / driver error | Qt print errors are caught, mapped to plain-language messages with suggested actions (check power/cable/Wi-Fi, choose another printer, spooler restart), and logged with a correlation id |
| No printers installed | The preview still works and can export PDF; a clear notice explains that no printer was detected and how to add one in Windows |
| Thermal printer without a matching profile | Suggested profiles offered; a mismatch warning shows measured overflow before printing |
| Very long content | Continuation pages with repeated headers, never clipped cells; a pre-print warning when a document exceeds a configured page count |
| Bengali text | Bundled font is always referenced in the template; if a font fails to load, the app blocks printing with an explicit error rather than printing boxes |
| Permissions | Printing/finalising is permission-gated (`prescription.print`, `invoice.print`, `finance.export`); denied attempts are audited, not silently ignored |
| Reprints | Tracked (`print_count`, `last_printed_at`, audit entry per print) with an optional "DUPLICATE" watermark on reprints (configurable) |

Preview provides: page navigation, zoom (fit-width/fit-page/percentage), print, PDF export, profile
switcher, and a warning strip listing any layout risks detected before printing (e.g. "1 medicine row
moved to page 2").

---

## 7. Determinism and versioning

- Same document + same profile ⇒ same layout; templates are versioned (`template_version` in the
  snapshot) so a future template change cannot silently restyle a historical reprint.
- Snapshots store the letterhead, dentist block, patient block, prices and catalogue names used at
  issue time; the renderer never re-reads current settings to fill historical documents.
- PDF output embeds the fonts, so a PDF opened on another machine (e.g. a pharmacy) shows Bengali
  correctly without requiring the font to be installed there.

---

## 8. Test matrix (`tests/printing/`)

| Dimension | Cases |
|---|---|
| Paper | A4 portrait/landscape, A5, A6, Letter, 80 mm roll, 58 mm roll, custom 100×150 mm |
| Content | 1 / 8 / 25 medicines; 1 / 40 invoice lines; 300-character Bengali complaint; 6 qualifications; 80-character patient names; long addresses; empty optional sections; 12-digit amounts; mixed Bangla/Latin/digits |
| Layout | No cell clipping, no overlap, header repetition, footer never split, signature ≥ 22 mm, no orphaned single row, page count within ±1 of the expected deterministic layout |
| Output | PDF renders to image, Bengali glyph presence check, font embedding check, text-extraction check for codes and totals, byte-stability check for repeated renders |
| Failure | Missing printer, unsupported page size, simulated device error, unsupported CSS in template, font-load failure |
| Performance | Prescription (2 pages) preview render ≤ 1 s; invoice (5 pages) ≤ 1.5 s; 500-page report streams without freezing the UI |

Every printed artefact used in acceptance testing is rendered to PNG/PDF under `tests/printing/artifacts/`
in CI and attached to the phase report so layout quality is reviewable, not asserted.

---

## 9. Known limitations (documented honestly)

- Windows-only printer specifics (driver quirks, Bluetooth pairing, spooler state) cannot be exercised in
  this Linux build environment; they are tested on GitHub Actions `windows-latest` with a simulated print
  engine, and the manual clean-machine checklist in Phase 17 covers a real printer/fax/PDF device.
- "Save as PDF" availability depends on the Windows "Microsoft Print to PDF" feature; the app always
  provides its own offline PDF export as a guaranteed path.
- Thermal printers that only accept ESC/POS raw commands are not supported directly; they are used through
  their Windows driver as a normal printer (the supported route for this product).
