Unicode true

!include "MUI2.nsh"
!include "x64.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define APP_NAME           "PolyWav Merger"
!define APP_EXE            "polywav_merger.exe"
!define APP_VERSION        "4.0.1"
!define APP_VERSION_LABEL  "Beta 4.0.1"
!define APP_PUBLISHER      "Atmo"
!define APP_URL            "https://atmo.studio"
!define APP_REGKEY         "Software\Microsoft\Windows\CurrentVersion\Uninstall\PolyWav Merger"
!define APP_INSTALL_REGKEY "Software\Atmo\PolyWav Merger"

Name "${APP_NAME} ${APP_VERSION_LABEL}"
BrandingText "${APP_PUBLISHER} — ${APP_NAME} ${APP_VERSION_LABEL}"
OutFile "dist_merged\PolyWav_Merger_Setup_${APP_VERSION}-beta.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "${APP_INSTALL_REGKEY}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
ShowInstDetails nevershow
ShowUninstDetails nevershow

VIProductVersion "4.0.1.0"
VIAddVersionKey "ProductName"      "${APP_NAME}"
VIAddVersionKey "ProductVersion"   "${APP_VERSION_LABEL}"
VIAddVersionKey "FileVersion"      "${APP_VERSION}"
VIAddVersionKey "FileDescription"  "${APP_NAME} ${APP_VERSION_LABEL} Installer"
VIAddVersionKey "CompanyName"      "${APP_PUBLISHER}"
VIAddVersionKey "LegalCopyright"   "© ${APP_PUBLISHER}"
VIAddVersionKey "InternalName"     "polywav_merger_setup"
VIAddVersionKey "OriginalFilename" "PolyWav_Merger_Setup_${APP_VERSION}-beta.exe"

!define MUI_ICON   "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_ABORTWARNING

!define MUI_WELCOMEPAGE_TITLE "Welcome to the ${APP_NAME} ${APP_VERSION_LABEL} Setup"
!define MUI_WELCOMEPAGE_TEXT  "This wizard will install ${APP_NAME} ${APP_VERSION_LABEL} on your computer.$\r$\n$\r$\n${APP_NAME} conforms recorder and TX WAV files into clean PolyWAV files with clock-drift correction.$\r$\n$\r$\nPublisher: ${APP_PUBLISHER}$\r$\n$\r$\nClick Next to continue."

!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_LINK         "Visit ${APP_PUBLISHER}"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"
!define MUI_FINISHPAGE_NOREBOOTSUPPORT

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Function .onInit
    SetRegView 64
    ; Detect a previous install and offer to remove it before continuing
    ReadRegStr $R0 HKLM "${APP_REGKEY}" "UninstallString"
    StrCmp $R0 "" done

    ReadRegStr $R1 HKLM "${APP_REGKEY}" "DisplayVersion"
    StrCmp $R1 "" 0 +2
        StrCpy $R1 "an earlier version"

    MessageBox MB_OKCANCEL|MB_ICONQUESTION \
        "${APP_NAME} ($R1) is already installed.$\r$\n$\r$\nDo you want to remove the previous version before installing ${APP_VERSION_LABEL}?" \
        /SD IDOK IDOK uninst
    Abort

uninst:
    ClearErrors
    ExecWait '$R0 /S _?=$INSTDIR'
done:
FunctionEnd

Section "${APP_NAME} (required)" SecCore
    SectionIn RO
    SetRegView 64
    SetOutPath "$INSTDIR"

    File "dist_merged\${APP_EXE}"
    File "/oname=polywav_merger.ico" "icon.ico"
    File "icon.png"

    ; App registration
    WriteRegStr HKLM "${APP_INSTALL_REGKEY}" "InstallDir"   "$INSTDIR"
    WriteRegStr HKLM "${APP_INSTALL_REGKEY}" "Version"      "${APP_VERSION_LABEL}"
    WriteRegStr HKLM "${APP_INSTALL_REGKEY}" "Publisher"    "${APP_PUBLISHER}"

    ; Add/Remove Programs entry
    WriteRegStr   HKLM "${APP_REGKEY}" "DisplayName"     "${APP_NAME} ${APP_VERSION_LABEL}"
    WriteRegStr   HKLM "${APP_REGKEY}" "DisplayVersion"  "${APP_VERSION_LABEL}"
    WriteRegStr   HKLM "${APP_REGKEY}" "Publisher"       "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${APP_REGKEY}" "URLInfoAbout"    "${APP_URL}"
    WriteRegStr   HKLM "${APP_REGKEY}" "URLUpdateInfo"   "${APP_URL}"
    WriteRegStr   HKLM "${APP_REGKEY}" "HelpLink"        "${APP_URL}"
    WriteRegStr   HKLM "${APP_REGKEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr   HKLM "${APP_REGKEY}" "DisplayIcon"     "$INSTDIR\polywav_merger.ico"
    WriteRegStr   HKLM "${APP_REGKEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr   HKLM "${APP_REGKEY}" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
    WriteRegDWORD HKLM "${APP_REGKEY}" "NoModify" 1
    WriteRegDWORD HKLM "${APP_REGKEY}" "NoRepair" 1

    ; Install date (YYYYMMDD)
    ${GetTime} "" "L" $0 $1 $2 $3 $4 $5 $6
    WriteRegStr HKLM "${APP_REGKEY}" "InstallDate" "$2$1$0"

    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Record installed size for Add/Remove Programs
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${APP_REGKEY}" "EstimatedSize" "$0"
SectionEnd

SectionGroup /e "Shortcuts" SecShortcuts
    Section "Start Menu shortcut" SecStartMenu
        CreateDirectory "$SMPROGRAMS\${APP_NAME}"
        CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"           "$INSTDIR\${APP_EXE}"     "" "$INSTDIR\polywav_merger.ico" 0
        CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe"
    SectionEnd

    Section "Desktop shortcut" SecDesktop
        CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\polywav_merger.ico" 0
    SectionEnd
SectionGroupEnd

LangString DESC_SecCore       ${LANG_ENGLISH} "Core application files (required)."
LangString DESC_SecShortcuts  ${LANG_ENGLISH} "Optional shortcuts."
LangString DESC_SecStartMenu  ${LANG_ENGLISH} "Add a shortcut to the Start Menu."
LangString DESC_SecDesktop    ${LANG_ENGLISH} "Add a shortcut to the Desktop."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecCore}      $(DESC_SecCore)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecShortcuts} $(DESC_SecShortcuts)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} $(DESC_SecStartMenu)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop}   $(DESC_SecDesktop)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
    SetRegView 64

    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
    RMDir  "$SMPROGRAMS\${APP_NAME}"

    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\icon.ico"
    Delete "$INSTDIR\polywav_merger.ico"
    Delete "$INSTDIR\icon.png"
    Delete "$INSTDIR\uninstall.exe"
    RMDir  "$INSTDIR"

    DeleteRegKey HKLM "${APP_INSTALL_REGKEY}"
    DeleteRegKey HKLM "${APP_REGKEY}"
SectionEnd
