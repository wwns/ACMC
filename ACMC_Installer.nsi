; ACMC Installer Script for NSIS
; Umieszcza aplikację z prawidłową ikoną LG.png

!include "MUI2.nsh"
!include "x64.nsh"

; ===== Ustawienia =====
Name "ACMC - Bramka Modbus LG"
OutFile "C:\Users\wiesl\ACMC\dist\ACMC_Setup.exe"
InstallDir "$PROGRAMFILES\ACMC"
RequestExecutionLevel admin

; MUI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Polish"

; ===== INSTALACJA =====
Section "Instalacja ACMC"
  SetOutPath "$INSTDIR"
  
  ; Kopiuj EXE
  File "C:\Users\wiesl\ACMC\dist\ACMC_AC.exe"
  
  ; Kopiuj ikonę LG.png do instalacji (dla shortcut'u)
  File "C:\Users\wiesl\ACMC\LG.png"
  
  ; Kopiuj wszystkie pliki Python (na wypadek potrzeby debugowania)
  File "C:\Users\wiesl\ACMC\*.py"
  File "C:\Users\wiesl\ACMC\*.db"
  
  ; Utwórz Start Menu shortcut z ikoną
  CreateDirectory "$SMPROGRAMS\ACMC"
  CreateShortCut "$SMPROGRAMS\ACMC\ACMC - Bramka Modbus.lnk" "$INSTDIR\ACMC_AC.exe" "" "$INSTDIR\LG.png" 0
  CreateShortCut "$SMPROGRAMS\ACMC\Odinstaluj.lnk" "$INSTDIR\Uninstall.exe"
  
  ; Utwórz Desktop shortcut z ikoną
  CreateShortCut "$DESKTOP\ACMC - Bramka Modbus.lnk" "$INSTDIR\ACMC_AC.exe" "" "$INSTDIR\LG.png" 0
  
  ; Utwórz uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

; ===== ODINSTALACJA =====
Section "Uninstall"
  Delete "$INSTDIR\ACMC_AC.exe"
  Delete "$INSTDIR\LG.png"
  Delete "$INSTDIR\*.py"
  Delete "$INSTDIR\*.db"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  
  Delete "$SMPROGRAMS\ACMC\*.lnk"
  RMDir "$SMPROGRAMS\ACMC"
  Delete "$DESKTOP\ACMC - Bramka Modbus.lnk"
SectionEnd
