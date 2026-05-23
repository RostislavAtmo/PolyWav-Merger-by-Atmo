; ═══════════════════════════════════════════════════════════════════════
; PolyWAV Builder beta 1.0  — Windows NSIS Installer
; ═══════════════════════════════════════════════════════════════════════

!include "MUI2.nsh"
!include "x64.nsh"

; ──────────────────────────────────────────────────────────────────────
; Main Settings
; ──────────────────────────────────────────────────────────────────────
Name "PolyWAV Builder beta 1.0"
OutFile "dist\PolyWAV_Builder_Setup.exe"
InstallDir "$PROGRAMFILES\PolyWAV Builder"
InstallDirRegKey HKCU "Software\PolyWAV Builder" ""
ShowInstDetails show
ShowUninstDetails show

; Product Version
VIProductVersion "1.0.0.0"
VIAddVersionKey ProductName "PolyWAV Builder"
VIAddVersionKey ProductVersion "1.0 beta"
VIAddVersionKey FileVersion "1.0.0.0"
VIAddVersionKey FileDescription "PolyWAV Builder - Recorder + TX Conform Tool"
VIAddVersionKey CompanyName "Atmo"
VIAddVersionKey LegalCopyright "Atmo"

; Installer icon
!define MUI_ICON "polywav_icon.ico"
!define MUI_UNICON "polywav_icon.ico"

; ──────────────────────────────────────────────────────────────────────
; MUI Settings
; ──────────────────────────────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "PolyWAV Builder beta 1.0"
!define MUI_WELCOMEPAGE_TEXT "Welcome to PolyWAV Builder Setup$\n$\nThis tool provides audio recording and TX file conforming.$\n$\nClick Next to continue."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_TITLE "Installation Complete"
!define MUI_FINISHPAGE_TEXT "PolyWAV Builder has been successfully installed.$\n$\nYou can launch the application from the Start Menu or Desktop shortcut."
!define MUI_FINISHPAGE_RUN "$INSTDIR\polywav_builder.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Run PolyWAV Builder Now"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ──────────────────────────────────────────────────────────────────────
; Language
; ──────────────────────────────────────────────────────────────────────
!insertmacro MUI_LANGUAGE "English"

; ══════════════════════════════════════════════════════════════════════
; Installer Sections
; ══════════════════════════════════════════════════════════════════════
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Main executable file
    File "dist\polywav_builder.exe"
    
    ; Logo and icon (for reference)
    File "logo_48.png"
    File "polywav_icon.ico"
    
    ; Write registry for uninstall
    WriteRegStr HKCU "Software\PolyWAV Builder" "" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PolyWAV Builder" \
        "DisplayName" "PolyWAV Builder beta 1.0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PolyWAV Builder" \
        "DisplayVersion" "1.0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PolyWAV Builder" \
        "Publisher" "Atmo"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PolyWAV Builder" \
        "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PolyWAV Builder" \
        "DisplayIcon" "$INSTDIR\polywav_icon.ico"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; ══════════════════════════════════════════════════════════════════════
; Shortcuts Section
; ══════════════════════════════════════════════════════════════════════
Section "Shortcuts"
    ; Start Menu folder
    CreateDirectory "$SMPROGRAMS\PolyWAV Builder"
    CreateShortcut "$SMPROGRAMS\PolyWAV Builder\PolyWAV Builder.lnk" \
        "$INSTDIR\polywav_builder.exe" "" \
        "$INSTDIR\polywav_icon.ico" 0
    CreateShortcut "$SMPROGRAMS\PolyWAV Builder\Uninstall.lnk" \
        "$INSTDIR\uninstall.exe"
    
    ; Desktop shortcut
    CreateShortcut "$DESKTOP\PolyWAV Builder.lnk" \
        "$INSTDIR\polywav_builder.exe" "" \
        "$INSTDIR\polywav_icon.ico" 0
SectionEnd

; ══════════════════════════════════════════════════════════════════════
; Uninstaller
; ══════════════════════════════════════════════════════════════════════
Section "Uninstall"
    ; Delete files
    Delete "$INSTDIR\polywav_builder.exe"
    Delete "$INSTDIR\logo_48.png"
    Delete "$INSTDIR\polywav_icon.ico"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Remove folder if empty
    RMDir "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\PolyWAV Builder\PolyWAV Builder.lnk"
    Delete "$SMPROGRAMS\PolyWAV Builder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\PolyWAV Builder"
    
    Delete "$DESKTOP\PolyWAV Builder.lnk"
    
    ; Remove registry
    DeleteRegKey HKCU "Software\PolyWAV Builder"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PolyWAV Builder"
SectionEnd
