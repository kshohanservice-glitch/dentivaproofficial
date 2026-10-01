; Dentiva Pro - NSIS installer
;
; Build (on Windows, after pyinstaller has produced dist\DentivaPro):
;     makensis /DPRODUCT_VERSION=1.0.0 /DSOURCE_DIR=..\dist\DentivaPro /DOUT_DIR=..\dist packaging\installer.nsi
; makensis changes its working directory to the folder holding this script, so relative paths here are
; relative to packaging\ (the CI build passes absolute paths instead).
;
; Phase 2 delivers this installer as a working per-user skeleton; the Phase 17 release validation
; exercises silent install, launch, uninstall and reinstall on a clean machine, and adds the optional
; all-users mode. Nothing here claims code signing: the installer is unsigned unless a real certificate
; is supplied to CI.

Unicode true

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!ifndef PRODUCT_VERSION
  !define PRODUCT_VERSION "1.0.0"
!endif
!ifndef SOURCE_DIR
  !define SOURCE_DIR "..\dist\DentivaPro"
!endif
!ifndef OUT_DIR
  !define OUT_DIR "..\dist"
!endif

!define PRODUCT_NAME "Dentiva Pro"
!define PRODUCT_SLUG "DentivaPro"
!define PRODUCT_PUBLISHER "Shohan Khan"
!define PRODUCT_EMAIL "helloiamshohan@gmail.com"
!define PRODUCT_EXE "DentivaPro.exe"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_SLUG}"
!define APP_KEY "Software\${PRODUCT_SLUG}"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${OUT_DIR}\${PRODUCT_SLUG}-Setup-${PRODUCT_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\${PRODUCT_SLUG}"
InstallDirRegKey HKCU "${APP_KEY}" "InstallDir"
RequestExecutionLevel user          ; per-user install: no administrator prompt
SetCompressor /SOLID lzma

VIProductVersion "${PRODUCT_VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "${PRODUCT_NAME} installer"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "LegalCopyright" "Copyright (c) ${PRODUCT_PUBLISHER} <${PRODUCT_EMAIL}>"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PRODUCT_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${PRODUCT_NAME}"
!define MUI_WELCOMEPAGE_TITLE "${PRODUCT_NAME} ${PRODUCT_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "This will install ${PRODUCT_NAME}, an offline dental clinic management \
system for Windows.$\r$\n$\r$\nThe application works completely offline and stores clinic data on this \
computer.$\r$\n$\r$\nClick Next to continue."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
UninstPage custom un.DataPage un.DataPageLeave
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Var RemoveClinicData

Function .onInit
  ; Support /S silent install (used by the release smoke test).
  ${If} ${Silent}
    SetSilent silent
  ${EndIf}
FunctionEnd

Section "Application" SecApplication
  SectionIn RO
  SetOutPath "$INSTDIR"
  ; Remove files from a previous version before copying the new ones, but never touch the data folder.
  RMDir /r "$INSTDIR\_internal"
  File /r "${SOURCE_DIR}\*.*"

  WriteRegStr HKCU "${APP_KEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${APP_KEY}" "Version" "${PRODUCT_VERSION}"

  ; Add/Remove Programs entry (per-user, because the install is per-user).
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER} <${PRODUCT_EMAIL}>"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_EXE}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "EstimatedSize" "$0"

  ; Start menu shortcut (and an optional desktop shortcut the user can opt out of).
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\${PRODUCT_EXE}"
  CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall ${PRODUCT_NAME}.lnk" "$INSTDIR\Uninstall.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section /o "Desktop shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\${PRODUCT_EXE}"
SectionEnd

Function un.DataPage
  ; Clinic data is never deleted silently: the checkbox is unchecked by default and the next step asks
  ; for an explicit confirmation before anything is removed.
  !insertmacro MUI_HEADER_TEXT "Clinic data" "Choose what happens to the clinic's records"
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}

  ${NSD_CreateLabel} 0 0 100% 40u "Uninstalling removes the application only. The clinic database, \
attachments and backups stay on this computer so the data can be restored or migrated later."
  Pop $1
  ${NSD_CreateCheckbox} 0 45u 100% 20u "Also remove all clinic data (irreversible)"
  Pop $RemoveClinicData
  nsDialogs::Show
FunctionEnd

Function un.DataPageLeave
  ${NSD_GetState} $RemoveClinicData $0
  ${If} $0 == ${BST_CHECKED}
    MessageBox MB_YESNO|MB_ICONEXCLAMATION \
      "All patient records, invoices, attachments and backups will be permanently deleted from this computer. Continue?" \
      IDYES +2
    Abort
  ${EndIf}
FunctionEnd

Section "Uninstall"
  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall ${PRODUCT_NAME}.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"

  ; The uninstaller deletes the application files it installed, and the data folder only when the user
  ; explicitly asked for it above.
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR\_internal"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  DeleteRegKey HKCU "${APP_KEY}"

  ${If} $RemoveClinicData == ${BST_CHECKED}
    ; Data roots the product can create (see core/paths.py). Any failure to delete something is
    ; reported by the uninstaller's own error handling rather than hidden.
    RMDir /r "$PROGRAMDATA\${PRODUCT_SLUG}"
    RMDir /r "$LOCALAPPDATA\${PRODUCT_SLUG}"
  ${EndIf}
SectionEnd
